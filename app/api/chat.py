import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import  Command

from app.agent.agent import get_agent, get_checkpointer
from app.api.auth import current_user_ctx
from app.api.revocation_demo import is_demo_session, stream_demo_chat
from app.schemas.chat import ChatRequest, RenameRequest, HistoryResponse, SessionListResponse, SessionActionResponse ,ResumeRequest
from app.services.history_service import get_file_chat_history
from app.services.hyde import llm
from app.utils.auth import get_current_user
from app.utils.redis_client import redis_client_connect as redis
from app.utils.semantic_cache import semantic_cache
from app.config.settings import get_settings
from app.agent.agent import _ACTION_WORDS , _MEMORY_WORDS

logger = logging.getLogger("rag.chat")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
s = get_settings()


def _sse_encode(text: str) -> str:
    """SSE 帧内容编码：JSON 字符串（含引号、真实换行）无损传输。

    之前用 text.replace('\\n', '\\\\n') 转义，会把真实换行与代码中的
    字面 \\n 混为一谈——前端还原时代码里的 \\n 字符串会被错误变成换行。
    JSON 编码语义明确：真实换行编码为 \\n，字面 \\n 编码为 \\\\\\n，
    前端 JSON.parse 即可无损还原。
    """
    return json.dumps(text, ensure_ascii=False)

_MEMORY_WORDS_FROM_AGENT = _MEMORY_WORDS

def _is_memory_request(question: str) -> bool:
    """记忆类问句：答案依赖对话历史，禁用缓存（读写双侧）"""
    return any(w in question for w in _MEMORY_WORDS)

def _is_action_request(question:str) -> bool:
    """判断问题是否包含动作词"""
    return any(word in question for word in _ACTION_WORDS)

# ── 会话标题（显示名，独立于 session_id 存储；重命名不影响 thread 记忆）──

_TITLE_FILE = "_meta.json"


def _load_titles(user_dir: str) -> dict:
    path = os.path.join(user_dir, _TITLE_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_title(user_dir: str, session_id: str, title: str) -> None:
    os.makedirs(user_dir, exist_ok=True)
    titles = _load_titles(user_dir)
    titles[session_id] = title
    with open(os.path.join(user_dir, _TITLE_FILE), "w", encoding="utf-8") as f:
        json.dump(titles, f, ensure_ascii=False)


def _delete_title(user_dir: str, session_id: str) -> None:
    titles = _load_titles(user_dir)
    if session_id in titles:
        titles.pop(session_id)
        with open(os.path.join(user_dir, _TITLE_FILE), "w", encoding="utf-8") as f:
            json.dump(titles, f, ensure_ascii=False)


def _generate_session_title(question: str) -> str:
    """用 LLM 生成简短会话标题（≤12 字）；失败时回退首句截断"""
    try:
        prompt = (
            "请用不超过 12 个字概括下面用户请求的主题，作为对话标题。"
            "直接输出标题本身，不要引号、句号或任何解释。\n\n"
            f"用户请求：{question[:200]}"
        )
        title = llm.invoke(prompt).content.strip().strip('"“”‘’。，！？：')
        if title:
            return title[:20]
    except Exception as e:
        logger.warning("会话标题生成失败，回退截断 | err=%s", e)
    return question[:12]

"""
流式输出接口
"""
@router.post("/stream")
@limiter.limit("10/minute")
async def stream_chat(request: Request, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["user_id"])
    t_start = time.time()
    if is_demo_session(body.session_id):
        return await stream_demo_chat(
            question=body.question,
            session_id=body.session_id,
            user_id=current_user["user_id"],
            memory_only=_is_memory_request(body.question),
            llm=llm,
            history_factory=get_file_chat_history,
        )
    if redis and not _is_action_request(body.question) and not _is_memory_request(body.question):
        # 1. 语义相似度缓存
        cached_answer = semantic_cache.lookup(body.question, user_id)
        if cached_answer:
            async def cache_stream():
                yield f"data: {_sse_encode(cached_answer)}\n\n"
                yield "data: [DONE]\n\n"
            logger.info("缓存命中 | type=semantic | user=%s | 耗时=%.2fs", user_id, time.time() - t_start)
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

        # 2. MD5 精确匹配缓存（兜底）
        question_hash = hashlib.md5(body.question.encode()).hexdigest()
        user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
        redis_chat_history = redis.get(user_key)
        if redis_chat_history:
            async def cache_stream():
                yield f"data: {_sse_encode(redis_chat_history)}\n\n"
                yield "data: [DONE]\n\n"
            logger.info("缓存命中 | type=md5 | user=%s | 耗时=%.2fs", user_id, time.time() - t_start)
            return StreamingResponse(cache_stream(), 200, media_type="text/event-stream")

    async def event_stream():
        t_start = time.time()
        all_request = ""
        frame_count = 0          # 输出的文本帧数（近似 token 数）
        tool_times: dict[str, float] = {}  # 工具名 → 开始时间，用于统计耗时
        blocked = False
        chat_history = get_file_chat_history(user_id=user_id, session_id=body.session_id)
        user_dir = os.path.join(s.CHAT_HISTORY_STORAGY_PATH, user_id)
        is_first_message = len(chat_history.messages) == 0   # 首条消息 → 触发自动标题
        logger.info("收到提问 | user=%s | session=%s | 问题=%s", user_id, body.session_id, body.question[:50])
        try:
            # chain = get_rag_chain(user_id)
            current_user_ctx.set(user_id)
            chain = get_agent()

            # 注入配置参数，指定 thread_id
            _config = {"configurable": {"thread_id": f"{user_id}_{body.session_id}"}}

            # ★ 入口防呆：该会话挂着待审批中断吗？（新增在流循环之前）
            snap0 = await chain.aget_state(_config)
            if any(task.interrupts for task in snap0.tasks):
                logger.info("会话存在待处理中断，新消息已拦截 | user=%s | session=%s",
                            user_id, body.session_id)
                yield f"data: {_sse_encode('[待处理审批] 当前会话有待确认的操作，请先完成审批后再继续对话')}\n\n"
                blocked = True
                return  # 不进图；finally 仍会执行

            # 流式生成
            async for event in chain.astream_events(
                {"messages": [("user", body.question)]},
                version="v2",
                config=_config
            ):
                e = event["event"]
                if e == "on_tool_start":
                    # 工具调用提示（Agent 推理轮输出的 tool_calls 在这里触发）
                    tool_name = event.get("name", "?")
                    tool_input = str(event["data"].get("input", ""))[:80]
                    tool_times[tool_name] = time.time()
                    logger.info("工具调用开始 | tool=%s | 输入=%s", tool_name, tool_input)
                    hint = f"[调用工具: {tool_name} | 输入: {tool_input}]"
                    yield f"data: {_sse_encode(hint)}\n\n"
                elif e == "on_chat_model_stream":
                    # token 级文本流：中间轮 function calling 的 content 为空会被跳过，
                    # 只有最终回答的文本会流出 → 打字机效果
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = "".join(
                            part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text"
                        )
                    else:
                        text = ""
                    if not text:
                        continue
                    all_request += text
                    frame_count += 1
                    yield f"data: {_sse_encode(text)}\n\n"
                elif e == "on_tool_end":
                    # 检测报告生成 → 推送下载链接（output 可能是 ToolMessage，取其 content）
                    tool_name = event.get("name", "?")
                    cost = time.time() - tool_times.get(tool_name, t_start)
                    output = event["data"].get("output")
                    logger.info("工具调用结束 | tool=%s | 耗时=%.2fs", tool_name, cost)
                    raw = getattr(output, "content", output)
                    if isinstance(raw, list):
                        raw = "".join(p.get("text", "") for p in raw if isinstance(p, dict))
                    raw = str(raw)
                    if "[REPORT_FILE]" in raw:
                        filename = raw.split("[REPORT_FILE]")[1].split("\n")[0].strip()
                        ok = bool(filename) and all(c.isalnum() or c in "._-" for c in filename) \
                            and filename.endswith((".md", ".docx", ".txt"))
                        if ok:
                            dl_html = f"<p><a href='/reports/{filename}' download class='download-link'>📥 下载报告：{filename}</a></p>"
                            all_request += dl_html  # 持久化到历史
                            yield f"data: {_sse_encode(dl_html)}\n\n"
                        else:
                            logger.warning("报告文件名解析异常，跳过链接推送 | %s", filename[:80])

            # 组装中断帧，获取工具中的payload返回给前端
            snap = await chain.aget_state(_config)
            interrupts = [i for task in snap.tasks for i in task.interrupts]
            if interrupts:
                first = interrupts[0]
                logger.info("检测到中断 | payload=%s", first.value)
                frame = {"type":"interrupt","payload":first.value,"interrupt_id":first.id}
                yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("流式对话异常 | user=%s | type=%s | repr=%r", user_id, type(e).__name__, e)
            if s.is_production:
                yield f"data: {_sse_encode('【系统错误】服务暂时不可用，请稍后重试')}\n\n"
            else:
                yield f"data: {_sse_encode('【系统错误】' + str(e))}\n\n"
        finally:
            if all_request and redis and not tool_times and not _is_memory_request(body.question): # not tool_times 表示没有调用工具，才进行缓存
                question_hash = hashlib.md5(body.question.encode()).hexdigest()
                user_key = f"{s.REDIS_USER_PREFIX}:{user_id}:{question_hash}"
                redis.setex(name=user_key, value=all_request, time=s.REDIS_EXPIRE)
                semantic_cache.store(body.question, user_id, all_request)
            if not blocked:
                history = chat_history
                history.add_message(HumanMessage(content=body.question))
                history.add_message(AIMessage(content=all_request))
            # ★ 首条消息 → 自动生成会话标题（LLM 概述；失败回退首句截断）
            if not blocked and is_first_message:
                title = await asyncio.to_thread(_generate_session_title, body.question)
                _save_title(user_dir, body.session_id, title)
                logger.info("会话标题已生成 | session=%s | title=%s", body.session_id, title)
            logger.info("对话完成 | user=%s | 耗时=%.2fs | 输出帧=%d | 回复长度=%d | 工具调用=%d",
                        user_id, time.time() - t_start, frame_count, len(all_request), len(tool_times))
            yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str, current_user: dict = Depends(get_current_user)):
    """获取会话历史"""
    history = get_file_chat_history(session_id,user_id=current_user["user_id"])
    # 将 BaseMessage 列表转为可序列化的字典列表
    messages = []
    for msg in history.messages:
        messages.append({
            "role": "human" if msg.type == "human" else "assistant",
            "content": msg.content
        })
    return {"messages": messages}

@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(current_user: dict = Depends(get_current_user)):
    """对话管理"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    user_dir = os.path.join(storage_path, user_id)

    if not os.path.exists(user_dir):
        return {"sessions": [], "session_meta": {}, "titles": {}}

    # 列出该目录下所有 .json 文件，提取会话 ID（去掉 .json 后缀；_ 开头为元数据文件）
    sessions = [
        f.replace('.json', '')
        for f in os.listdir(user_dir)
        if f.endswith('.json') and not f.startswith('_')
    ]
    # 会话最后更新时间（文件 mtime，供前端排序 / 时间分组）
    session_meta = {
        sid: datetime.fromtimestamp(
            os.path.getmtime(os.path.join(user_dir, f"{sid}.json"))
        ).strftime("%Y-%m-%d %H:%M")
        for sid in sessions
    }
    return {"sessions": sessions, "session_meta": session_meta, "titles": _load_titles(user_dir)}


@router.delete("/session/{session_id}", response_model=SessionActionResponse)
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """删除指定会话"""
    user_id = str(current_user["user_id"])
    storage_path = s.CHAT_HISTORY_STORAGY_PATH
    file_path = os.path.join(storage_path, user_id, f"{session_id}.json")

    if not os.path.exists(file_path):
        return {"code": 404, "message": "会话不存在"}

    os.remove(file_path)
    await get_checkpointer().adelete_thread(f"{user_id}_{session_id}")
    # 同步清理标题记录
    _delete_title(os.path.join(storage_path, user_id), session_id)
    return {"code": 200, "message": f"会话 {session_id} 已删除"}


@router.put("/session/{session_id}/rename", response_model=SessionActionResponse)
async def rename_session(session_id: str, request: RenameRequest, current_user: dict = Depends(get_current_user)):
    """重命名会话标题（仅修改显示标题；session_id 与 thread 记忆不受影响）"""
    user_id = str(current_user["user_id"])
    user_dir = os.path.join(s.CHAT_HISTORY_STORAGY_PATH, user_id)
    new_name = request.new_name.strip()

    _save_title(user_dir, session_id, new_name)
    logger.info("会话重命名 | user=%s | session=%s | 新标题=%s", user_id, session_id, new_name)
    return {"code": 200, "message": "重命名成功", "data": {"new_name": new_name}}

@router.post("/resume")
@limiter.limit("10/minute")
async def resume_interrupt(request:Request,resume_request: ResumeRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["user_id"])
    body = resume_request
    _config = {"configurable": {"thread_id": f"{user_id}_{body.session_id}"}}

    async def event_stream():
        t_start = time.time()
        frame_count = 0          # 输出的文本帧数（近似 token 数）
        all_request = ""
        tool_times: dict[str,float] = {}
        chat_history = get_file_chat_history(user_id=user_id, session_id=body.session_id)
        try:
            # 1. 入口校验：没有中断 → 拒绝（与 /stream 的防呆互补
            chain = get_agent()
            snap = await chain.aget_state(_config)
            if not any(task.interrupts for task in snap.tasks):
                yield f"data: {_sse_encode('[无处理审批] 当前会话没有待确认的操作，请继续对话')}\n\n"
                return
        #     2. resume 流
            async for event in chain.astream_events(
                Command(resume=body.decision),
                version="v2",
                config=_config
            ):
                e = event["event"]
                if e == "on_tool_start":
                    # 工具调用提示（Agent 推理轮输出的 tool_calls 在这里触发）
                    tool_name = event.get("name", "?")
                    tool_input = str(event["data"].get("input", ""))[:80]
                    tool_times[tool_name] = time.time()
                    logger.info("工具调用开始 | tool=%s | 输入=%s", tool_name, tool_input)
                    hint = f"[调用工具: {tool_name} | 输入: {tool_input}]"
                    yield f"data: {_sse_encode(hint)}\n\n"
                elif e == "on_chat_model_stream":
                    # token 级文本流：中间轮 function calling 的 content 为空会被跳过，
                    # 只有最终回答的文本会流出 → 打字机效果
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = "".join(
                            part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text"
                        )
                    else:
                        text = ""
                    if not text:
                        continue
                    all_request += text
                    frame_count += 1
                    yield f"data: {_sse_encode(text)}\n\n"
                elif e == "on_tool_end":
                    # 检测报告生成 → 推送下载链接（resume 分支；output 可能是 ToolMessage）
                    tool_name = event.get("name", "?")
                    cost = time.time() - tool_times.get(tool_name, t_start)
                    output = event["data"].get("output")
                    logger.info("工具调用结束 | tool=%s | 耗时=%.2fs", tool_name, cost)
                    raw = getattr(output, "content", output)
                    if isinstance(raw, list):
                        raw = "".join(p.get("text", "") for p in raw if isinstance(p, dict))
                    raw = str(raw)
                    if "[REPORT_FILE]" in raw:
                        filename = raw.split("[REPORT_FILE]")[1].split("\n")[0].strip()
                        ok = bool(filename) and all(c.isalnum() or c in "._-" for c in filename) \
                            and filename.endswith((".md", ".docx", ".txt"))
                        if ok:
                            dl_html = f"<p><a href='/reports/{filename}' download class='download-link'>📥 下载报告：{filename}</a></p>"
                            all_request += dl_html  # 持久化到历史
                            yield f"data: {_sse_encode(dl_html)}\n\n"
                        else:
                            logger.warning("报告文件名解析异常，跳过链接推送 | %s", filename[:80])

            # 组装中断帧，获取工具中的payload返回给前端
            snap = await chain.aget_state(_config)
            interrupts = [i for task in snap.tasks for i in task.interrupts]
            if interrupts:
                first = interrupts[0]
                logger.info("检测到中断 | payload=%s", first.value)
                frame = {"type":"interrupt","payload":first.value,"interrupt_id":first.id}
                yield f"data: {json.dumps(frame,ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("恢复执行异常 | user=%s | type=%s | repr=%r", user_id, type(e).__name__, e)
            yield f"data: {_sse_encode('【系统错误】'+str(e))}\n\n"
        finally:
            if all_request:
                chat_history.add_message(AIMessage(content=all_request))
            yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/pending/{session_id}")
async def check_pending(session_id: str,current_user: dict = Depends(get_current_user)):
    """检查待处理"""
    user_id = str(current_user["user_id"])
    _config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
    chain = get_agent()
    snap = await chain.aget_state(_config)
    interrupts = [i for task in snap.tasks for i in task.interrupts]
    if interrupts:
        first = interrupts[0]
        logger.info("检测到中断 | payload=%s", first.value)
        return {"interrupt": {"type": "interrupt", "payload": first.value, "interrupt_id": first.id}}
    else :
        return {"interrupt": None}
