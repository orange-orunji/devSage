# -*- coding: utf-8 -*-
"""首字延迟优化：HyDE 按需启用 + BM25 并行 + 可配置开关。

背景（实测日志）：
    HyDE 生成+向量检索 10.78s | Rerank 2.27s | 总 13.06s
HyDE 是一次完整的大模型调用，是首字延迟的主要构成；而 BM25 与 HyDE 互不依赖，
可以并行。对"关键词型/短问题"，HyDE 收益有限，跳过可省下约 10s。
"""
import io

ROOT = r"D:\phython\RAG_Personal"

# ── 1) settings 增加开关 ──
p = ROOT + r"\app\config\settings.py"
s = io.open(p, encoding="utf-8").read()
if "HYDE_MODE" not in s:
    anchor = 'CHROMA_NAME: str = "enterprise_knowledge"'
    s = s.replace(anchor, anchor + '''

    # ── HyDE 开关（首字延迟优化，2026-11-20）──
    # auto: 仅语义类且足够长的问题用 HyDE；on: 全部启用；off: 全部禁用
    HYDE_MODE: str = "auto"
    HYDE_MIN_CHARS: int = 15''')
    io.open(p, "w", encoding="utf-8").write(s)
print("settings.HYDE_MODE:", "HYDE_MODE" in io.open(p, encoding="utf-8").read())

# ── 2) hyde.py：按需 HyDE + BM25 并行 ──
p2 = ROOT + r"\app\services\hyde.py"
h = io.open(p2, encoding="utf-8").read()

helper = '''

def _should_hyde(question: str, route: str) -> bool:
    """是否启用 HyDE：auto 模式下仅语义类且长度足够时启用。"""
    mode = (getattr(s, "HYDE_MODE", "auto") or "auto").lower()
    if mode == "off":
        return False
    if mode == "on":
        return True
    min_chars = getattr(s, "HYDE_MIN_CHARS", 15)
    return route == "semantic" and len(question.strip()) >= min_chars
'''
if "_should_hyde" not in h:
    h = h.replace("\ndef generate_hypothetical(", helper + "\ndef generate_hypothetical(")

old_body = '''    t_start = time.time()
    # 1.HyDE 假想向量检索
    t0 = time.time()
    hypo_text = generate_hypothetical(question)
    vector = _vs.get_vector(query=hypo_text, k=k_vector)
    logger.info("HyDE 生成+向量检索 | 耗时=%.2fs | 召回=%d | query=%s", time.time() - t0, len(vector), question[:50])

    # 2.BM25 关键词检索
    t0 = time.time()
    search = service.search(question, top_k=k_keyword)
    logger.info("BM25 关键词检索 | 耗时=%.2fs | 召回=%d", time.time() - t0, len(search))'''

new_body = '''    from concurrent.futures import ThreadPoolExecutor

    t_start = time.time()

    # 1 + 2. BM25 与 HyDE 并行：BM25 不依赖 HyDE 结果
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=1) as pool:
        bm25_future = pool.submit(service.search, question, k_keyword)
        use_hyde = _should_hyde(question, "keyword")
        hypo_text = generate_hypothetical(question) if use_hyde else question
        vector = _vs.get_vector(query=hypo_text, k=k_vector)
        logger.info("HyDE=%s 向量检索 | 耗时=%.2fs | 召回=%d | query=%s",
                    "开" if use_hyde else "跳过", time.time() - t0, len(vector), question[:50])
        search = bm25_future.result()
    logger.info("BM25 关键词检索（并行）| 耗时=%.2fs | 召回=%d", time.time() - t0, len(search))'''

if old_body in h:
    h = h.replace(old_body, new_body)
    io.open(p2, "w", encoding="utf-8").write(h)
    print("hyde_plus_rerank_bm25_retrieve 已改为并行 + 按需 HyDE")
else:
    print("警告：未匹配到目标代码块，未修改")

# ── 3) 语义路由也走同一开关 ──
h2 = io.open(p2, encoding="utf-8").read()
old_sem = '''def hyde_plus_rerank_retrieve(question : str, k : int = 3):'''
if "def hyde_plus_rerank_retrieve" in h2:
    # 在其函数体内把 generate_hypothetical 换成条件调用
    idx = h2.index(old_sem)
    end = h2.index("def hyde_plus_rerank_bm25_retrieve", idx)
    seg = h2[idx:end]
    if "use_hyde" not in seg:
        seg2 = seg.replace("vector = _vs.get_vector(query=generate_hypothetical(question), k=k)",
                           "use_hyde = _should_hyde(question, \"semantic\")\n"
                           "    q = generate_hypothetical(question) if use_hyde else question\n"
                           "    vector = _vs.get_vector(query=q, k=k)")
        h2 = h2[:idx] + seg2 + h2[end:]
        io.open(p2, "w", encoding="utf-8").write(h2)
        print("语义检索分支已加开关:", "use_hyde" in seg2)
