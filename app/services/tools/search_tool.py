from langchain_core.documents import Document
from langchain_core.tools import tool
from typing import List

from app.services.hyde import adaptive_retrieve
import logging


@tool
def search_knowledge_base(query: str) -> list[str]:
    """在企业知识库中搜索文档内容。

    内部流程：查询意图路由 → 模糊语义问题走 HyDE 单路（HyDE 语义扩展 + 向量检索），
    精确关键词问题走向量检索 + BM25 双路 RRF 融合，最后 Rerank 重排序。
    返回：top-3 最相关文档片段。

    ✅ 必须调用的情况：
    - "XX文档里怎么说的"
    - "有没有关于XX的资料"
    - "知识库里XX是什么"

    ❌ 不要调用的情况：
    - "今天天气怎么样"（知识库没有）
    - "帮我写一段代码"（这是生成任务，不是检索）
    - 用户只是闲聊
    """
    logger = logging.getLogger("rag.tools")
    logger.info("Agent 调用了 search_knowledge_base | query=%s", query)

    #  意图路由 → semantic 走 HyDE 单路 / keyword 走双路 RRF 融合
    docs = adaptive_retrieve(query)
    return [f"【来源：{d.metadata.get('source')}】\n{d.page_content}" for d in docs]
