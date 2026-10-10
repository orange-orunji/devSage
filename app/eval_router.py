"""
查询路由器校准脚本

用途：
1. 用评测集问题（300 条，按 type 字段分模糊组/精确组）检验 query_router 的意图判定
2. 打印每条问题的 max_IDF 数值分布，用于校准 IDF_THRESHOLD

运行方式（项目根目录）：
    python -m app.eval_router

注意：本脚本会触发 Chroma / Embedding 初始化，需保证 .env 配置可用
"""
import os
import json
import sys

import jieba

# 直接运行（python app/eval_router.py）时 sys.path[0] 是 app/，补上仓库根，
# 与 docstring 推荐的 `python -m app.eval_router` 两种跑法等价
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import vector_store_service as vs
from app.services.bm25_service import bm25_service
from app.services.tools.query_router import query_router, PATTERN, CN_FACT_PATTERN, IDF_THRESHOLD


def max_idf_of(query: str):
    """复刻路由器第二层逻辑，但返回 (命中词, max_IDF) 供观察分布"""
    idf = bm25_service.bm25.idf
    tokens = [w for w in jieba.cut(query) if len(w.strip()) > 1]
    scored = [(w, idf.get(w)) for w in tokens]
    hit = [(w, s) for w, s in scored if s is not None]
    if not hit:
        return None, 0.0
    top_word, top_score = max(hit, key=lambda x: x[1])
    return top_word, top_score


def main():
    # ── 构建 BM25 索引（脚本不启动 FastAPI，需手动建）──
    all_docs = vs.get_all_documents()
    bm25_service.build_index(all_docs)
    print(f"BM25 索引构建完成 | 文档数={len(all_docs)} | 当前阈值={IDF_THRESHOLD}\n")

    # ── 加载评测集 ──
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "eval_questions.json"), "r", encoding="utf-8") as f:
        questions = json.load(f)

    # 按 type 字段分组（semantic=模糊组，keyword=精确组）
    semantic_items = [q for q in questions if q.get("type") == "semantic"]
    keyword_items = [q for q in questions if q.get("type") == "keyword"]
    groups = [("模糊组", semantic_items), ("精确组", keyword_items)]

    total_right = total_all = 0
    for group_name, items in groups:
        print(f"════════ {group_name}（{len(items)} 条）════════")
        hit_cnt = 0
        for i, item in enumerate(items, 1):
            q = item["question"]
            # 记录路由器走了哪一层
            if PATTERN.search(q) or CN_FACT_PATTERN.search(q):
                layer, intent = "正则层", "keyword"
            else:
                intent = query_router(q)
                layer = "IDF层" if intent == "keyword" else "默认层"
            top_word, top_score = max_idf_of(q)

            # 期望：模糊组判 semantic，精确组判 keyword
            expected = "semantic" if group_name == "模糊组" else "keyword"
            ok = intent == expected
            hit_cnt += ok
            mark = "✓" if ok else "✗ 误判!"
            word_str = f"{top_word}({top_score:.2f})" if top_word else "无命中词"
            print(f"{i:>2}. [{intent:<8}|{layer}] max_IDF={top_score:>5.2f} {word_str:<20} {mark} {q}")

        total_right += hit_cnt
        total_all += len(items)
        print(f"→ {group_name} 判定正确率: {hit_cnt}/{len(items)} = {hit_cnt / len(items):.2%}\n")

    print(f"总体判定正确率: {total_right}/{total_all} = {total_right / total_all:.2%}")
    print("\n校准建议：观察上面两组 max_IDF 的数值分界——")
    print("  若模糊组误判 keyword → 调高 IDF_THRESHOLD")
    print("  若精确组误判 semantic → 调低 IDF_THRESHOLD")


if __name__ == "__main__":
    main()
