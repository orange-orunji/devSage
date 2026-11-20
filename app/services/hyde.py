import time
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.services.bm25_service import bm25_service
from app.services.rerank import rerank
from app.config.settings import get_settings
from app.services.tools.query_router import query_router
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("rag.retrieval")

s = get_settings()
_vs = VectorStoreService(embedding_model=None)
service = bm25_service

llm = ChatOpenAI(
    model=s.SILICON_MODEL,
    api_key=s.SILICON_API_KEY,
    base_url=s.SILICON_BASE_URL,
    streaming=True,
    callbacks=[]
)

def generate_hypothetical(question : str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个文档写作助手。请根据用户的问题，写一段可能出现在相关文档中的答案/假想文本"),
        ("human", "{question}")
    ])
    messages = prompt.format_messages(question=question)
    content = llm.invoke(messages)
    return content.content
# 原版hyde检索
def hyde_retrieve(question : str,k : int = 3):
    return _vs.get_vector(query=generate_hypothetical(question),k=k)

# rerank后hyde检索
def hyde_plus_rerank_retrieve(question : str, k : int = 3):
    vector = _vs.get_vector(query=generate_hypothetical(question), k=k)
    return rerank(query=question,docs=vector,top_k=k)

    #hy​de检索后进行BM25计算后返回rank
def hyde_plus_rerank_bm25_retrieve(question : str, k_vector: int = 15, k_keyword: int = 10, final_k: int = 3):
    t_start = time.time()
    # 1.HyDE 假想向量检索
    t0 = time.time()
    hypo_text = generate_hypothetical(question)
    vector = _vs.get_vector(query=hypo_text, k=k_vector)
    logger.info("HyDE 生成+向量检索 | 耗时=%.2fs | 召回=%d | query=%s", time.time() - t0, len(vector), question[:50])

    # 2.BM25 关键词检索
    t0 = time.time()
    search = service.search(question, top_k=k_keyword)
    logger.info("BM25 关键词检索 | 耗时=%.2fs | 召回=%d", time.time() - t0, len(search))

    # 3. RRF 倒数排名融合（替代旧的暴力拼接去重）
    # 分数 = Σ 1/(k + rank)，k=60；只看排名不看原始分数，免归一化
    t0 = time.time()
    RRF_K = 60
    fused = {}  # {page_content: [累计 RRF 分数, doc 对象]}
    for rank, doc in enumerate(vector, start=1):
        item = fused.setdefault(doc.page_content, [0.0, doc])
        item[0] += 1 / (RRF_K + rank)
    for rank, doc in enumerate(search, start=1):
        item = fused.setdefault(doc.page_content, [0.0, doc])
        item[0] += 1 / (RRF_K + rank)  # 双路都召回 → 累加，共识文档排名提升
    unique_docs = [doc for _, doc in sorted(fused.values(), key=lambda x: x[0], reverse=True)]
    logger.info("RRF 融合 | 耗时=%.2fs | 合并前=%d | 去重后=%d | 双路共识=%d",
                time.time() - t0, len(vector) + len(search), len(unique_docs),
                len(vector) + len(search) - len(unique_docs))

    # 4. Rerank 重排序
    t0 = time.time()
    result = rerank(question, unique_docs, top_k=final_k)
    logger.info("Rerank 重排序 | 耗时=%.2fs | 最终=%d | 总耗时=%.2fs",
                time.time() - t0, len(result), time.time() - t_start)

    return result

def adaptive_retrieve(question: str, k: int = 3):
    router = query_router(question)
    if router == "semantic":
        return hyde_plus_rerank_retrieve(question, k)
    # 注意：hyde_plus_rerank_bm25_retrieve 的位置参数是 k_vector，最终数量要用 final_k 传
    return hyde_plus_rerank_bm25_retrieve(question, final_k=k)


if __name__ == "__main__":
    # 直接运行时需手动配置日志级别（默认 WARNING 会吞掉 info）
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
    # 服务运行时由 main.py lifespan 构建索引；直接跑需手动建，否则 BM25 路为空
    service.build_index(_vs.get_all_documents())

    q = "Redis 默认持久化方式"
    docs = adaptive_retrieve(q)
    print("检索到的文档片段：")
    for doc in docs:
        print(doc.page_content[:200])
        print("---")