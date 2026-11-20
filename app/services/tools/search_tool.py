import time
from collections import OrderedDict

from langchain_core.documents import Document
from langchain_core.tools import tool
from typing import List

from app.services.hyde import adaptive_retrieve
import logging

# ── 检索结果短时缓存（同一问题的重复调用直接命中，避免重复向量化与重排）──
_SEARCH_CACHE: "OrderedDict[str, tuple[float, list[str]]]" = OrderedDict()
_SEARCH_TTL = 120.0      # 秒
_SEARCH_MAX = 256        # 条数上限


def _cache_get(key: str):
    hit = _SEARCH_CACHE.get(key)
    if not hit:
        return None
    ts, value = hit
    if time.time() - ts > _SEARCH_TTL:
        _SEARCH_CACHE.pop(key, None)
        return None
    _SEARCH_CACHE.move_to_end(key)
    return value


def _cache_put(key: str, value: list[str]):
    _SEARCH_CACHE[key] = (time.time(), value)
    _SEARCH_CACHE.move_to_end(key)
    while len(_SEARCH_CACHE) > _SEARCH_MAX:
        _SEARCH_CACHE.popitem(last=False)


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
    key = " ".join(query.split()).lower()
    cached = _cache_get(key)
    if cached is not None:
        logger.info("检索命中缓存 | query=%s | 片段=%d", query, len(cached))
        return cached

    logger.info("Agent 调用了 search_knowledge_base | query=%s", query)

    #  意图路由 → semantic 走 HyDE 单路 / keyword 走双路 RRF 融合
    docs = adaptive_retrieve(query)
    result = [f"【来源：{d.metadata.get('source')}】\n{d.page_content}" for d in docs]
    _cache_put(key, result)
    return result
