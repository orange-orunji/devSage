from langchain_core.messages import SystemMessage , trim_messages
from langgraph.graph import StateGraph, MessagesState ,START , END
from langgraph.prebuilt import  ToolNode
from langchain_openai import ChatOpenAI
from functools import lru_cache

import re
import logging

from app.config.settings import get_settings
from app.services.hyde import adaptive_retrieve
from app.services.tools.upload_tool import upload_document
from app.services.tools.status_tool import get_document_status,generate_report,convert_format,send_email
from app.services.tools.search_tool import search_knowledge_base
from app.services.tools.delete_tool import delete_document
from app.services.tools.web_search_tool import search_web

s = get_settings()
_tools = [
         upload_document,
         get_document_status,
         search_knowledge_base,
         generate_report,
         convert_format,
         send_email,
         delete_document,
     ]
_llm = ChatOpenAI(
            model=s.SILICON_MODEL,
            api_key=s.SILICON_API_KEY,
            base_url=s.SILICON_BASE_URL,
            streaming=True,
            callbacks=[],
            temperature=0.3, #  知识场景低温度，压制采样漂移
        ).bind_tools(_tools)

_SYSTEM_PROMPT = """你是智维台，面向研发与 IT 支持团队的知识库助手。对用户的每个问题，你直接给出答案（必要时基于系统提供的检索/联网数据），像同事对话一样自然；你的回答永远以答案本身开头。

## 核心原则（必须严格遵守）
**所有用户提问，若已有【知识库检索结果】上下文，直接基于它回答；仅当上下文不足以回答时，才调用 search_knowledge_base 补充。**
**【知识库检索结果】【联网搜索结果】是系统给你的可靠数据，直接作为事实使用，按规范标注来源即可；不要把它们转述成"示例/假想/素材/文档"——它们就是真实数据。**
不得未经检索就直接凭训练知识回答。

## 唯一例外（可以不调 search_knowledge_base）
- 用户说"谢谢"、"好的"等纯社交用语
- 数学计算（如"1+1等于几"）
- 用户明确说"不用查文档，直接告诉我"

## 其他工具
- 用户说"上传"、"帮我存"、"加进知识库" → 调用 upload_document
- 用户问"知识库有什么"、"有多少文档" → 调用 get_document_status
- 用户要求生成报告时调用 -> generate_report
- 用户要求转换文件格式调用 -> convert_format
- 用户要求将文件/消息进行邮件发送调用 -> send_email
- 用户要求删除文件 -> delete_document

- 联网内容需标注:"根据网络搜索: <URL>"

## 回答要求
- 第一句话就是答案内容，答案与来源标注一次写成。示范：
  问：北京今天天气怎么样？
  答：北京今天白天晴间多云，19~31℃，北转南风二三级，昼夜温差大。
     根据网络搜索：https://news.bjd.com.cn/...
- 检索到相关内容时：优先引用文档内容，标注"根据知识库文档："
- 检索结果为空时：回答"知识库中未找到相关内容"，然后可补充通用知识并标注"根据通用知识："
- 知识库内容与通用知识冲突时：以知识库为准
- 输出 Markdown 表格时：表格与表格、表格与段落之间必须用空行分隔；每个表格行必须以 | 开头和结尾，不得跨行
- 引用知识库内容时在句末标注（来源：文档名）；回答末尾列'引用来源'小节
"""

_checkpointer = None
_GREET_WORDS = ["你好","hello","hi","谢谢","你是谁"]
_MEMORY_WORDS = ["记得", "记不记得", "记住",       # 记忆动词
    "我刚才", "刚刚", "我之前", "之前我", "刚才" ,   # 指代上文
    "上次", "上一次", "我说过", "我说了", "我问过",  # 回溯表达
    "我叫什么", "我的名字", "上面说", "前面说",      # 自指/位置指代
]
_ACTION_WORDS = ["删除", "删掉", "移除", "清理", "去掉", "上传", "存入",
                 "入库", "保存", "导出", "有哪些文档", "多少文档","多少个文档","文档数",
                 "帮我发送这份报告", "帮我统计一下"]
_ACTION_PATTERNS = [
    r"发.{0,3}邮件",
    r"生成.{0,3}报告",
    r"转.{0,3}(Word|word|格式)",
]
_MATH_PATTERNS = [
    r"^\s*[\d\s+\-*/().=×÷？?]+\s*$",   # 纯算式整句："1+1 等于几？"
    r"等于几", r"等于多少", r"算一下", r"计算一下",  # 口语问法
]
_RETRIEVAL_MIN_SCORE = 0.1      # 前置检索质量阈值：低于此分视为"无有效结果"→ 联网兜底

# 裁剪消息
_trimmer = trim_messages(
    max_tokens=20,   # 配合 token_counter=len —— 语义是"最多保留 20 条消息"
    token_counter=len,
    strategy="last",#策略: 保留最新的
    start_on="human",# ★ 从 human 起头（工具对/轮次完整性）
    allow_partial=False,
    include_system=False, # system 是节点里现拼的，不在裁剪范围
)

# 注入检查点，用于保存中间状态，防止无状态的图被缓存
def set_checkpointer(cp):
    global _checkpointer
    _checkpointer = cp

def get_checkpointer():
    return _checkpointer

class AgentState(MessagesState):
    retrieval_context: str = ""
    web_context: str = ""


def router(state: AgentState) -> str:
    q = str(state["messages"][-1].content)
    if any(k in q for k in _GREET_WORDS):
        return "skip"
    if any(k in q for k in _MEMORY_WORDS):
        return "skip"
    if any(re.search(p, q) for p in _MATH_PATTERNS):
        return "skip"
    if any(k in q for k in _ACTION_WORDS) or \
       any(re.search(p,q) for p in _ACTION_PATTERNS):  # 动作类 → skip
        return "skip"
    return "retrieve"

def check_retrieve_none_router(state: AgentState) -> str:
    if state["retrieval_context"] == "":
        return "web"
    else:
        return "agent"

def retrieve(state: AgentState) -> dict:
    question = state["messages"][-1].content
    docs = adaptive_retrieve(question)
    docs = [d for d in docs if d.metadata.get("rerank_score", 0.0) >= _RETRIEVAL_MIN_SCORE]
    docs_text =  "\n\n".join(
        f"【来源: {d.metadata.get('source')}】\n{d.page_content}" for d in docs
    )
    return {"retrieval_context": docs_text}


async def call_model(state: AgentState) -> dict:
    system = _SYSTEM_PROMPT
    ctx = state.get("retrieval_context","")
    if ctx:
        system += f"\n\n【知识库检索结果】\n{ctx}"
    web = state.get("web_context", "")
    if web:
        system += f"\n\n【工具返回：联网搜索（系统已验证的真实数据，直接引用，勿转述为示例/文档）】\n{web}"
    msgs = [SystemMessage(content=system)] + _trimmer.invoke(state["messages"])
    logger = logging.getLogger("rag.agent")
    logger.info("记忆窗口 | 发送=%d 条 | 全量=%d 条", len(msgs), len(state["messages"]))
    response = await _llm.ainvoke(msgs)
    return {"messages": [response]}

def web_search_node(state: AgentState) -> dict:
    q = str(state["messages"][-1].content)
    text = search_web(q)
    logger = logging.getLogger("rag.agent")
    if text.startswith("联网搜索失败"):
        logger.warning("联网搜索失败 | %s | %s", q, text[:80])
        return {}
    logger.info("联网搜索 | %s | 命中%d条", q, text.count("【网页："))
    return {
        "web_context": text
    }

def continues(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "END"

# 重置状态
def reset(state: AgentState) -> dict:
    return {"retrieval_context": "", "web_context": ""}


@lru_cache(maxsize=None)
def get_agent():
    builder = StateGraph(AgentState)

    builder.add_node("reset", reset)

    builder.add_node("retrieve", retrieve)
    builder.add_node("agent",call_model)
    builder.add_node("web",web_search_node)
    builder.add_node("tools",ToolNode(_tools))

    builder.add_edge(START, "reset")
    builder.add_conditional_edges("reset", router , {"retrieve": "retrieve", "skip": "agent"})
    builder.add_conditional_edges("retrieve",check_retrieve_none_router,{"web":"web" , "agent": "agent"})
    builder.add_edge("web","agent")
    builder.add_conditional_edges("agent",continues,{"tools":"tools","END":END})
    builder.add_edge("tools","agent")

    return builder.compile(checkpointer=_checkpointer)