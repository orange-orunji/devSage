import os
import json
import sys
import time

# 直接运行（python app/eval_retrieval.py）时 sys.path[0] 是 app/，仓库根不在
# 搜索路径上，`from app...` 会 ModuleNotFoundError——补上仓库根，使
# `python app/eval_retrieval.py` 与 `python -m app.eval_retrieval` 两种跑法等价
# （同 scripts/ci_check_import.py、eval_agent.py 的既有做法）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import vector_store_service as vs
from app.services.bm25_service import bm25_service
from app.services.hyde import hyde_plus_rerank_retrieve, hyde_retrieve,hyde_plus_rerank_bm25_retrieve,adaptive_retrieve
from app.services.rerank import rerank

# 独立运行本脚本时手动构建 BM25 索引（服务运行时由 main.py lifespan 构建）
bm25_service.build_index(vs.get_all_documents())

# 评估指标函数
def recall_at_k(docs, keywords, k=3):
    """Top-K 中是否包含至少一个预期关键词"""
    for doc in docs[:k]:
        if any(kw in doc.page_content for kw in keywords):
            return True
    return False

def reciprocal_rank(docs, keywords):
    """第一个正确答案的排名倒数"""
    for i, doc in enumerate(docs):
        if any(kw in doc.page_content for kw in keywords):
            return 1.0 / (i + 1)
    return 0.0

# 不同检索策略
def baseline_retrieve(query: str, k=3):
    return vs.get_vector(query, k=k)

def hyde_only(query: str, k=3):
    # hyde_retrieve 内部可能已包含 Rerank？请根据实际调整
    return hyde_retrieve(query, k=k)

def hyde_plus_rerank(query: str, k=3):
    """HyDE 召回 10 个候选，再用 Rerank 精排取前 k 个"""
    # 用 Rerank 精排
    return hyde_plus_rerank_retrieve(query, k=k)
def hyde_plus_rerank_bm25(query: str, k=3):
    """HyDE 召回 10 个候选，再用 Rerank 精排取前 k 个"""
    # 用 Rerank 精排
    return hyde_plus_rerank_bm25_retrieve(question=query,final_k=k)
def adaptive_retrieves(query: str, k=3):
    """意图路由：semantic 走 HyDE 单路，keyword 走双路 RRF 融合，最后 Rerank 取前 k 个"""
    return adaptive_retrieve(question=query, k=k)

# 加载测试问题
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(BASE_DIR, "eval_questions.json")
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    test_questions = json.load(f)

# ── 断点续跑：评测结果按 (策略名, 题号) 落盘，重跑时自动跳过已完成项 ──
CHECKPOINT_FILE = os.path.join(BASE_DIR, "eval_checkpoint.json")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_checkpoint(cache, name, idx, hit_flag, rr):
    cache.setdefault(name, {})[str(idx)] = {"hit": bool(hit_flag), "rr": rr}
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

def retrieve_with_retry(retriever, q, k, retries=3):
    """瞬时网络故障（如 WinError 10054 连接被重置）退避重试"""
    for attempt in range(1, retries + 1):
        try:
            return retriever(q, k=k)
        except Exception as e:
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"    ⚠ 检索失败（第 {attempt}/{retries} 次），{wait}s 后重试：{type(e).__name__}: {e}")
            time.sleep(wait)

# 评估函数
def evaluate(name, retriever, k=3):
    total = len(test_questions)
    cache = load_checkpoint()
    done = cache.get(name, {})
    hit = sum(1 for v in done.values() if v["hit"])
    mrr_sum = sum(v["rr"] for v in done.values())
    skipped = len(done)
    if skipped:
        print(f"[{name}] 断点续跑：已完成 {skipped}/{total}，跳过这些题")
    for idx, item in enumerate(test_questions, 1):   # 从1开始计数，更直观
        if str(idx) in done:
            continue
        q = item["question"]
        keywords = item["expected_keywords"]
        try:
            docs = retrieve_with_retry(retriever, q, k)
        except Exception as e:
            # 重试耗尽仍失败：按未命中记 0 分继续，避免整轮报废（结果中会单独提示）
            print(f"    ✗ 第 {idx} 题重试耗尽，按未命中处理：{type(e).__name__}: {e}")
            docs = []
        hit_flag = recall_at_k(docs, keywords, k)
        rr = reciprocal_rank(docs, keywords)
        if hit_flag:
            hit += 1
        mrr_sum += rr
        save_checkpoint(cache, name, idx, hit_flag, rr)
        # 进度打印（加在这里）
        print(f"[{name}] 处理第 {idx}/{total} 个问题：{q[:40]}...")
    recall = hit / total
    mrr = mrr_sum / total
    print(f"{name}: Recall@{k} = {recall:.2%}, MRR = {mrr:.3f}")

# 运行对比（请根据你的 hyde_retrieve 内部实现决定是否需要 hyde_plus_rerank）
# evaluate("Baseline", baseline_retrieve, k=1)
# evaluate("HyDEOnly", hyde_only, k=1)
# evaluate("HyDE_plus_rerank", hyde_plus_rerank, k=1)
# evaluate("hyde_plus_rerank_bm25", hyde_plus_rerank_bm25, k=1)
# 语料已扩充至 38 切片：同场重跑混合基线 + 路由策略，保证对比公平
evaluate("hyde_plus_rerank_bm25", hyde_plus_rerank_bm25, k=1)
evaluate("adaptive_retrieve", adaptive_retrieves, k=1)
# Baseline: Recall@1 = 60.00%, MRR = 0.600
# HyDE+Rerank: Recall@1 = 63.33%, MRR = 0.633


# TODO 将模糊类型数据和准确分析数据分开来查询再进行对比
"""
    语义化问题情况下查询
    纯模糊测试结果:
    Baseline: Recall@1 = 53.33%, MRR = 0.533
    HyDEOnly: Recall@1 = 60.00%, MRR = 0.600
    HyDE_plus_rerank: Recall@1 = 66.67%, MRR = 0.667
    hyde_plus_rerank_bm25: Recall@1 = 50.00%, MRR = 0.500
    
    HyDE+Rerank 在纯模糊语义场景下是最优的
    BM25 不是万能的，它需要配合精确查询才能体现优势
    
    
    添加13条专为 BM25 精确匹配设计的测试数据后
    Baseline: Recall@1 = 41.86%, MRR = 0.419
    HyDEOnly: Recall@1 = 51.16%, MRR = 0.512
    HyDE_plus_rerank: Recall@1 = 48.84%, MRR = 0.488
    hyde_plus_rerank_bm25: Recall@1 = 39.53%, MRR = 0.395
    
    
    
    
    HyDE_plus_rerank: Recall@1 = 51.67%, MRR = 0.517

    HyDE_plus_rerank: Recall@1 = 50.67%, MRR = 0.528
    hyde_plus_rerank_bm25: Recall@1 = 56.67%, MRR = 0.567
    adaptive_retrieve: Recall@1 = 56.67%, MRR = 0.567  # 19 切片旧语料

    # 38 切片新语料（同场双策略重跑）：
    hyde_plus_rerank_bm25: Recall@1 = 57.67%, MRR = 0.577
    adaptive_retrieve: Recall@1 = 59.67%, MRR = 0.597  # 反超基线 +2pp
AC3-WQ
"""