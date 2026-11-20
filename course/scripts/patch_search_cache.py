"""按 TTL 缓存检索工具结果，避免同一轮内重复检索。

背景：日志显示一次问答里 search_knowledge_base 会被调用两次
（状态图必经检索节点 + 模型主动调用），第二次耗时 12.6s 且结果相同。
"""
import io

p = r"D:\phython\RAG_Personal\app\services\tools\search_tool.py"
s = io.open(p, encoding="utf-8").read()

if "_SEARCH_CACHE" in s:
    print("已存在缓存逻辑，跳过")
else:
    s = s.replace(
        '''from langchain_core.documents import Document
from langchain_core.tools import tool
from typing import List

from app.services.hyde import adaptive_retrieve
import logging
''',
        '''import time
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
''')

    s = s.replace(
        '''    logger = logging.getLogger("rag.tools")
    logger.info("Agent 调用了 search_knowledge_base | query=%s", query)

    #  意图路由 → semantic 走 HyDE 单路 / keyword 走双路 RRF 融合
    docs = adaptive_retrieve(query)
    return [f"【来源：{d.metadata.get('source')}】\\n{d.page_content}" for d in docs]''',
        '''    logger = logging.getLogger("rag.tools")
    key = " ".join(query.split()).lower()
    cached = _cache_get(key)
    if cached is not None:
        logger.info("检索命中缓存 | query=%s | 片段=%d", query, len(cached))
        return cached

    logger.info("Agent 调用了 search_knowledge_base | query=%s", query)

    #  意图路由 → semantic 走 HyDE 单路 / keyword 走双路 RRF 融合
    docs = adaptive_retrieve(query)
    result = [f"【来源：{d.metadata.get('source')}】\\n{d.page_content}" for d in docs]
    _cache_put(key, result)
    return result''')

    io.open(p, "w", encoding="utf-8").write(s)
    print("已加入检索缓存：", "_SEARCH_CACHE" in s, "| 命中分支：", "_cache_get(key)" in s)
