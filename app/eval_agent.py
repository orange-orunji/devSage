# -*- coding: utf-8 -*-
"""Agent 端到端评测：分组成功率 + 工具命中 + 引用/联网断言 + P95 耗时

设计原则（对齐 eval_retrieval.py 风格）：
  · 全自动零 LLM judge：工具命中对照流内 [调用工具:] 提示；引用/联网用正则；
    关键词子串匹配（OR 语义，宽松防误杀）
  · 分组 category（kb/action/web/memory/social）——诊断价值
  · 断点续跑：结果按题号落盘 eval_agent_checkpoint.json

运行前提：
  1) 后端已启动（BASE 可配）
  2) 建议先清 Redis 缓存，保证冷缓存基线不被历史条目污染
用法：python -m app.eval_agent（或 python app/eval_agent.py，已做路径引导）
"""
import asyncio
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(errors="replace")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))

import httpx  # noqa: E402

BASE = "http://127.0.0.1:8010"
USER, PASS = "test", "123456"
QUESTIONS_FILE = os.path.join(BASE_DIR, "eval_agent_questions.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "eval_agent_checkpoint.json")

CITE_RE = re.compile(r"(【来源|（来源|\(来源|引用来源|来源[:：])")
TOOL_RE = re.compile(r"\[调用工具[:：]\s*(\w+)")

# 滑动窗口节流：60 秒内最多 8 个请求（服务限流 10/min，留余量）
_REQ_TIMES = []


async def throttle():
    now = time.time()
    _REQ_TIMES[:] = [t for t in _REQ_TIMES if now - t < 60]
    if len(_REQ_TIMES) >= 8:
        wait = 61 - (now - _REQ_TIMES[0])
        if wait > 0:
            await asyncio.sleep(wait)
    _REQ_TIMES.append(time.time())


async def consume(client, path, payload, headers):
    """消费 SSE → {text, tools, interrupt, frames}"""
    await throttle()
    text, tools, interrupt, frames = "", [], False, 0
    async with client.stream("POST", f"{BASE}{path}", json=payload, headers=headers) as resp:
        if resp.status_code != 200:
            return {"text": f"HTTP {resp.status_code}", "tools": [], "interrupt": False, "frames": 0}
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            raw = line[6:].strip()
            if raw == "[DONE]":
                break
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict):
                if obj.get("type") == "interrupt":
                    interrupt = True
                continue
            if obj.startswith("[调用工具"):
                m = TOOL_RE.search(obj)
                if m:
                    tools.append(m.group(1))
                continue
            text += obj
            frames += 1
    return {"text": text, "tools": tools, "interrupt": interrupt, "frames": frames}


def judge(expect, res):
    if expect.get("observe"):          # 观察题：不断言内容，但排除请求异常
        if res["text"].startswith("HTTP"):
            return (False, [f"请求异常: {res['text'][:20]}"])
        return (True, [])
    fails = []
    for t in expect.get("must_call_tools", []):
        if t not in res["tools"]:
            fails.append(f"缺少工具调用 {t}（实际: {res['tools'] or '无'}）")
    if expect.get("must_cite") and not CITE_RE.search(res["text"]):
        fails.append("缺少来源引用")
    if expect.get("no_cite") and CITE_RE.search(res["text"]):
        fails.append("不应出现来源引用")
    if expect.get("web_used"):
        has_mark = ("【网页：" in res["text"]) or ("根据网络搜索" in res["text"])
        has_url = re.search(r"https?://", res["text"]) is not None
        if not (has_mark and has_url):
            fails.append("未使用联网兜底（需同时含【网页:/根据网络搜索 + 真实链接）")
    kws = expect.get("keywords")
    if kws and not any(k in res["text"] for k in kws):
        fails.append(f"关键词未命中 {kws}")
    if expect.get("interrupt_expected") and not res["interrupt"]:
        fails.append("未出现中断帧")
    return (len(fails) == 0, fails)


async def run_one(client, headers, item, idx):
    sid = f"eval_{idx:02d}"
    t0 = time.perf_counter()
    try:
        await client.delete(f"{BASE}/api/chat/session/{sid}", headers=headers)
        # setup 轮（铺垫记忆，不计分）
        for s in item.get("setup", []):
            await consume(client, "/api/chat/stream", {"question": s, "session_id": sid}, headers)
        # 测试轮
        res = await consume(client, "/api/chat/stream", {"question": item["q"], "session_id": sid}, headers)
        # 中断题：自动取消并合并恢复流文本
        if res["interrupt"]:
            res2 = await consume(client, "/api/chat/resume", {"session_id": sid, "decision": False}, headers)
            res["text"] += res2["text"]
    except Exception as e:                      # 超时/断连不崩全批，记失败继续
        return {"idx": idx, "q": item["q"], "category": item["category"],
                "passed": False, "fails": [f"异常中断: {type(e).__name__}"],
                "elapsed": round(time.perf_counter() - t0, 1), "tools": [], "head": ""}
    elapsed = time.perf_counter() - t0
    passed, fails = judge(item["expect"], res)
    return {
        "idx": idx, "q": item["q"], "category": item["category"],
        "passed": passed, "fails": fails, "elapsed": round(elapsed, 1),
        "tools": res["tools"], "head": res["text"][:80],
    }


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(cache):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


async def main():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    total = len(questions)
    cache = load_checkpoint()
    done = cache.get("results", {})
    if done:
        print(f"断点续跑：已完成 {len(done)}/{total}，跳过")

    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{BASE}/api/auth/login", json={"username": USER, "password": PASS})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print("登录成功，开始评测\n")
        for idx, item in enumerate(questions, 1):
            if str(idx) in done:
                continue
            res = await run_one(client, headers, item, idx)
            mark = "✓" if res["passed"] else "✗"
            print(f"[{idx}/{total}] {mark} [{res['category']}] {res['q'][:32]} | {res['elapsed']}s"
                  + (f" | 失败: {'; '.join(res['fails'])}" if res["fails"] else ""))
            done[str(idx)] = res
            cache["results"] = done
            save_checkpoint(cache)
            await asyncio.sleep(3)   # 限流保护（10/min）

    # ── 报告 ──
    results = [cache["results"][str(i)] for i in range(1, total + 1) if str(i) in cache["results"]]
    if not results:
        print("无结果")
        return
    ok = sum(1 for x in results if x["passed"])
    cats = {}
    for x in results:
        c = cats.setdefault(x["category"], [0, 0])
        c[1] += 1
        if x["passed"]:
            c[0] += 1
    times = sorted(x["elapsed"] for x in results)
    p95 = times[min(len(times) - 1, int(len(times) * 0.95))]
    avg = sum(times) / len(times)

    print("\n" + "=" * 16 + " Agent 端到端评测报告 " + "=" * 16)
    print(f"总数 {len(results)} | 通过 {ok} | 成功率 {ok / len(results):.1%}")
    for c in ["kb", "action", "web", "memory", "social"]:
        if c in cats:
            p, n = cats[c]
            print(f"  ├─ {c:7s} {p}/{n} ({p / n:.0%})")
    print(f"耗时：平均 {avg:.1f}s | P95 {p95:.1f}s")
    cat_times = {}
    for x in results:
        cat_times.setdefault(x["category"], []).append(x["elapsed"])
    print("分类延迟（联网/报告类拖 P95，需拆开看）：")
    for c in ["kb", "action", "web", "memory", "social"]:
        if c in cat_times:
            ts = sorted(cat_times[c])
            c_avg = sum(ts) / len(ts)
            c_p95 = ts[min(len(ts) - 1, int(len(ts) * 0.95))]
            print(f"  ├─ {c:7s} 均 {c_avg:.1f}s | P95 {c_p95:.1f}s")
    failed = [x for x in results if not x["passed"]]
    if failed:
        print("失败明细：")
        for x in failed:
            print(f"  [{x['idx']}] [{x['category']}] {x['q'][:30]} → {'; '.join(x['fails'])}")
            print(f"      回答: {x['head']!r}")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
