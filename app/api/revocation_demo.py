"""仅使用假文档的单进程撤权实验；权限状态在服务重启后恢复关闭。"""

import json
import logging
import re
from threading import RLock

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, StrictBool

from app.utils.auth import get_current_user

router = APIRouter(prefix="/demo", tags=["模拟撤权实验"])
logger = logging.getLogger("rag.revocation_demo")

# 仅对应本次已核对的测试账号，不代表正式业务角色。
DEMO_OWNER_ID = 1  # test
DEMO_READER_ID = 2  # test1
DEMO_DOCUMENT_TEXT = "测试数字为 739184"
_reader_allowed = False
_permission_version = 0
_permission_lock = RLock()


class PermissionBody(BaseModel):
    allowed: StrictBool


@router.put("/permission", summary="由 test 调整 test1 的假文档读取权限")
def set_permission(
    body: PermissionBody,
    user: dict = Depends(get_current_user),
):
    user_id = user.get("user_id")
    if user_id != DEMO_OWNER_ID:
        raise HTTPException(status_code=403, detail="无权修改实验权限")

    global _reader_allowed, _permission_version
    with _permission_lock:
        if _reader_allowed != body.allowed:
            _permission_version += 1
        _reader_allowed = body.allowed
    logger.info(
        "模拟权限调整 | operator=%s | reader=%s | allowed=%s",
        user_id,
        DEMO_READER_ID,
        _reader_allowed,
    )
    return {"allowed": _reader_allowed}


def _permission_stamp(user_id: int) -> int:
    """读取、缓存与流式返回共用的当前权限检查。"""
    with _permission_lock:
        if user_id == DEMO_OWNER_ID:
            return 0
        if user_id == DEMO_READER_ID and _reader_allowed:
            return _permission_version
    logger.info("模拟文档读取 | user=%s | result=denied", user_id)
    raise HTTPException(status_code=403, detail="没有读取权限")


def _same_permission(user_id: int, stamp: int) -> bool:
    with _permission_lock:
        return user_id == DEMO_OWNER_ID or (
            user_id == DEMO_READER_ID
            and _reader_allowed
            and _permission_version == stamp
        )


@router.get("/document", summary="按当前实验权限读取假文档")
def read_document(user: dict = Depends(get_current_user)):
    user_id = user.get("user_id")
    _permission_stamp(user_id)
    logger.info("模拟文档读取 | user=%s | result=allowed", user_id)
    return {"text": DEMO_DOCUMENT_TEXT}


def is_demo_session(session_id: str) -> bool:
    return session_id.startswith("d20_")


def _sse_frame(text: str) -> str:
    return f"data: {json.dumps(text, ensure_ascii=False)}\n\n"


async def stream_demo_chat(
    *, question, session_id, user_id, memory_only, llm, history_factory,
):
    """假文档每次直接读取且不读写缓存；历史回顾仅用于核验撤权边界。"""
    if not re.fullmatch(r"d20_[A-Za-z0-9_-]{1,80}", session_id):
        raise HTTPException(status_code=400, detail="实验会话编号请使用 d20_ 开头的字母、数字、下划线或短横线")
    if user_id not in (DEMO_OWNER_ID, DEMO_READER_ID):
        raise HTTPException(status_code=403, detail="无权使用撤权实验")

    # 假文档查询每次检查权限并直接读取；旧缓存即使存在，也不会被使用。
    # 回顾历史不重新读取文档，不将其误记为撤权清除成功。
    stamp = None if memory_only else _permission_stamp(user_id)
    history = history_factory(user_id=str(user_id), session_id=session_id)
    history_messages = history.messages[-20:]
    logger.info(
        "实验聊天 | user=%s | session=%s | mode=%s | cache=%s",
        user_id, session_id, "history-only" if memory_only else "document",
        "bypass-history" if memory_only else "bypass-document",
    )

    async def event_stream():
        answer = ""
        try:
            if memory_only:
                system = (
                    "这是使用假数据的会话边界实验。本轮只能根据提供的历史消息回答，"
                    "没有对应记录时只回答“不知道”。不调用工具，不重新查询文档，不猜测。"
                )
            else:
                if not _same_permission(user_id, stamp):
                    yield _sse_frame("【实验读取已停止】权限已变更，请重新发起请求。")
                    yield "data: [DONE]\n\n"
                    return
                system = (
                    "这是使用假数据的撤权实验。仅根据下列已授权假文档回答，"
                    "资料不足时回答“不知道”，不调用工具。\n"
                    + DEMO_DOCUMENT_TEXT
                )
                logger.info("实验文档读取 | user=%s | result=allowed", user_id)
            messages = [
                SystemMessage(content=system),
                *history_messages,
                HumanMessage(content=question),
            ]
            async for chunk in llm.astream(messages):
                if not memory_only and not _same_permission(user_id, stamp):
                    yield _sse_frame("【实验读取已停止】权限已变更，请重新发起请求。")
                    break
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
                answer += text
                if text:
                    yield _sse_frame(text)
        except Exception:
            logger.exception("实验聊天生成失败 | user=%s | session=%s", user_id, session_id)
            yield _sse_frame("【实验错误】生成失败，请查看服务端日志。")
        finally:
            if answer:
                history.add_message(HumanMessage(content=question))
                history.add_message(AIMessage(content=answer))
            if memory_only:
                logger.info(
                    "实验历史边界 | user=%s | session=%s | history_messages=%s | "
                    "contains_test_value=%s | document_retrieved=False",
                    user_id, session_id, len(history_messages), "739184" in answer,
                )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
