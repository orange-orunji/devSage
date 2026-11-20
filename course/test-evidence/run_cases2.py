# -*- coding: utf-8 -*-
"""测试执行（稳健版）：逐用例 try/except，结果增量落盘。"""
import json
import os
import random
import string
import time
import traceback

import requests

BASE = "http://127.0.0.1:9000"
OUT_DIR = r"D:\课设\_test"
os.makedirs(OUT_DIR, exist_ok=True)
TAG = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
USER = {"username": "t_" + TAG, "password": "Test@2026_" + TAG}
RESULTS = []
TOK = {"v": None}


def save():
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump({"user": USER["username"], "ran_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "base": BASE, "results": RESULTS}, f, ensure_ascii=False, indent=1)


def rec(cid, name, module, expected, actual, ok, ms=None, note=""):
    RESULTS.append({"id": cid, "name": name, "module": module, "expected": expected,
                    "actual": actual, "status": "PASS" if ok else "FAIL", "ms": ms, "note": note})
    print("[%s] %-9s %-26s %s" % ("PASS" if ok else "FAIL", cid, name, (actual or "")[:70]))
    save()


def blocked(cid, name, module, expected, why):
    RESULTS.append({"id": cid, "name": name, "module": module, "expected": expected,
                    "actual": "未执行：" + why, "status": "BLOCK", "ms": None, "note": why})
    print("[BLOCK] %-9s %-26s %s" % (cid, name, why))
    save()


def case(cid, name, module, expected, fn):
    t0 = time.time()
    try:
        ok, actual, note = fn()
        rec(cid, name, module, expected, actual, ok, int((time.time() - t0) * 1000), note or "")
    except Exception as e:
        rec(cid, name, module, expected, "异常：" + type(e).__name__ + " " + str(e)[:60], False,
            int((time.time() - t0) * 1000))
        print(traceback.format_exc()[-300:])


H = lambda: {"Authorization": "Bearer " + TOK["v"]} if TOK["v"] else {}


def stream_chat(question, sid):
    payload = {"question": question, "session_id": sid}
    t = time.time()
    first, text, code = None, "", None
    with requests.post(BASE + "/api/chat/stream", json=payload, headers=H(),
                       stream=True, timeout=180) as resp:
        code = resp.status_code
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip().strip('"')
            if first is None:
                first = time.time() - t
            text += chunk
    return code, text, time.time() - t, first


# 1 健康
case("MISC-01", "服务健康检查", "基础", "200 且 status=ok", lambda: (
    (lambda r: (r.status_code == 200 and "ok" in r.text, "%d %s" % (r.status_code, r.text[:40]), ""))(
        requests.get(BASE + "/health", timeout=60))))

# 2 认证
case("AUTH-01", "注册新用户", "M1 认证", "200 注册成功", lambda: (
    (lambda r: (r.status_code == 200, "%d %s" % (r.status_code, r.text[:60]), ""))(
        requests.post(BASE + "/api/auth/register", json=USER, timeout=60))))

case("AUTH-02", "重复注册被拒", "M1 认证", "4xx 提示已存在", lambda: (
    (lambda r: (400 <= r.status_code < 500, "%d %s" % (r.status_code, r.text[:60]), ""))(
        requests.post(BASE + "/api/auth/register", json=USER, timeout=60))))


def do_login():
    r = requests.post(BASE + "/api/auth/login", json=USER, timeout=60)
    tok = None
    if r.status_code == 200:
        tok = r.json().get("access_token")
        TOK["v"] = tok
    return (r.status_code == 200 and bool(tok),
            "%d token_len=%d" % (r.status_code, len(tok or "")), "")


case("AUTH-03", "正确口令登录", "M1 认证", "200 且返回 access_token", do_login)

case("AUTH-04", "错误口令登录", "M1 认证", "401 不返回令牌", lambda: (
    (lambda r: (r.status_code == 401, "%d %s" % (r.status_code, r.text[:50]), ""))(
        requests.post(BASE + "/api/auth/login", json={"username": USER["username"], "password": "bad-123"},
                      timeout=60))))

case("AUTH-05", "令牌换取用户信息", "M1 认证", "200 且 username 一致", lambda: (
    (lambda r: (r.status_code == 200 and USER["username"] in r.text, "%d %s" % (r.status_code, r.text[:60]), ""))(
        requests.get(BASE + "/api/auth/me", headers=H(), timeout=60))))

case("AUTH-06", "无令牌访问受保护接口", "M1 认证", "401", lambda: (
    (lambda r: (r.status_code in (401, 403), "%d" % r.status_code, ""))(
        requests.get(BASE + "/api/chat/sessions", timeout=60))))


def do_chpwd():
    new = "NewPass@2026"
    r = requests.post(BASE + "/api/auth/me/password", headers=H(),
                      json={"old_password": USER["password"], "new_password": new}, timeout=60)
    if r.status_code != 200:
        return (False, "%d %s" % (r.status_code, r.text[:60]), "")
    r2 = requests.post(BASE + "/api/auth/login",
                       json={"username": USER["username"], "password": new}, timeout=60)
    if r2.status_code == 200:
        USER["password"] = new
        TOK["v"] = r2.json().get("access_token")
    return (r2.status_code == 200, "改密=%d, 新密码登录=%d" % (r.status_code, r2.status_code), "")


case("AUTH-07", "修改密码并复登录", "M1 认证", "200 且新密码可登录", do_chpwd)

# 3 对话
store = {}


def do_chat1():
    code, text, total, first = stream_chat("这个知识库现在收录了哪些文档？", "demo_exec")
    store["t1"] = text
    return (code == 200 and len(text) > 20 and (first or 99) <= 3.0,
            "code=%d 首字=%.1fs 总=%.1fs 字数=%d" % (code, first or -1, total, len(text)), "")


case("CHAT-01", "流式问答主流程", "M4 检索问答", "200，逐段输出，首字 ≤3s", do_chat1)


def do_chat4():
    t = store.get("t1", "")
    return ("来源" in t, "答案含'来源'=%s" % ("来源" in t), "")


case("CHAT-04", "引用来源可追溯", "M4 检索问答", "答案含来源标注", do_chat4)


def do_chat2():
    code, text, total, first = stream_chat("那第二点具体怎么做？", "demo_exec")
    return (code == 200 and len(text) > 20, "code=%d 字数=%d 总=%.1fs" % (code, len(text), total), "")


case("CHAT-02", "多轮上下文追问", "M4 检索问答", "200 且回应上一轮", do_chat2)

case("CHAT-06", "空问题被拒", "M4 检索问答", "422 参数校验", lambda: (
    (lambda r: (r.status_code in (400, 422), "%d" % r.status_code, ""))(
        requests.post(BASE + "/api/chat/stream", headers=H(), json={"question": "", "session_id": "demo_exec"},
                      timeout=60))))

# 4 限流
def do_limit():
    codes = []
    for _ in range(12):
        try:
            c, _, _, _ = stream_chat("1+1", "rate_probe")
            codes.append(c)
        except Exception as e:
            codes.append(type(e).__name__)
        if 429 in codes:
            break
    return (429 in codes, "返回码=%s" % codes[:12], "slowapi 10/minute")


case("CHAT-05", "问答接口限流", "M4 检索问答", "第 11 次起 429", do_limit)

# 5 文档
sample = os.path.join(OUT_DIR, "smoke_%s.txt" % TAG)
open(sample, "w", encoding="utf-8").write("智维台上线检查清单\n1. 健康检查通过\n2. 知识库可检索\n")


def do_upload():
    with open(sample, "rb") as f:
        r = requests.post(BASE + "/api/document/upload", headers=H(),
                          files={"file": ("smoke_%s.txt" % TAG, f, "text/plain")}, timeout=600)
    return (r.status_code in (200, 202), "%d %s" % (r.status_code, r.text[:90]), "")


case("DOC-01", "上传 txt 文档", "M3 文档", "200/202 受理", do_upload)

bad = os.path.join(OUT_DIR, "bad_%s.exe" % TAG)
open(bad, "wb").write(b"MZ fake")


def do_badfmt():
    with open(bad, "rb") as f:
        r = requests.post(BASE + "/api/document/upload", headers=H(),
                          files={"file": ("bad_%s.exe" % TAG, f, "application/octet-stream")}, timeout=300)
    return (400 <= r.status_code < 500, "%d %s" % (r.status_code, r.text[:70]), "")


case("DOC-03", "上传不支持格式", "M3 文档", "4xx 拒绝", do_badfmt)

case("DOC-05", "文档与切片统计", "M3 文档", "200 返回统计", lambda: (
    (lambda r: (r.status_code == 200, "%d %s" % (r.status_code, r.text[:90]), ""))(
        requests.get(BASE + "/api/document/stats", headers=H(), timeout=120))))

# 6 会话
case("SESS-01", "会话列表", "M2 会话", "200 返回数组", lambda: (
    (lambda r: (r.status_code == 200, "%d %s" % (r.status_code, r.text[:70]), ""))(
        requests.get(BASE + "/api/chat/sessions", headers=H(), timeout=60))))

case("SESS-02", "读取会话历史", "M2 会话", "200 且有消息", lambda: (
    (lambda r: (r.status_code == 200 and len(r.text) > 50, "%d 长度=%d" % (r.status_code, len(r.text)), ""))(
        requests.get(BASE + "/api/chat/history/demo_exec", headers=H(), timeout=60))))

case("SESS-06", "不存在会话不串数据", "M2 会话", "空结果或 404", lambda: (
    (lambda r: (r.status_code in (200, 404) and len(r.text) < 200, "%d 长度=%d" % (r.status_code, len(r.text)), ""))(
        requests.get(BASE + "/api/chat/history/none_%s" % TAG, headers=H(), timeout=60))))

# 7 安全
case("SEC-04", "登录框 SQL 注入", "M6 安全", "401 无堆栈", lambda: (
    (lambda r: (r.status_code == 401, "%d %s" % (r.status_code, r.text[:50]), ""))(
        requests.post(BASE + "/api/auth/login", json={"username": "' OR 1=1 --", "password": "x"}, timeout=60))))

case("SEC-01", "伪造令牌访问", "M6 安全", "401", lambda: (
    (lambda r: (r.status_code in (401, 403), "%d" % r.status_code, ""))(
        requests.get(BASE + "/api/document/stats", headers={"Authorization": "Bearer invalid.token.val"}, timeout=60))))

blocked("CHAT-07", "模型不可用降级", "M4 检索问答", "明确错误提示", "需断网/清空密钥，影响并行用例")
blocked("TOOL-01", "报告生成与下载", "M5 交付工具", "返回报告文件", "长链路，验收演示中人工验证")
blocked("TOOL-02", "邮件审批拦截", "M5 交付工具", "弹审批卡片", "需前端交互，人工验证")
blocked("COMP-01", "浏览器兼容主流程", "兼容性", "布局与流式正常", "需人工视觉验证")

s = {}
for r_ in RESULTS:
    s[r_["status"]] = s.get(r_["status"], 0) + 1
lat = [r_["ms"] for r_ in RESULTS if r_["ms"]]
s["avg_ms"] = int(sum(lat) / len(lat)) if lat else 0
s["max_ms"] = max(lat) if lat else 0
out = json.load(open(os.path.join(OUT_DIR, "results.json"), encoding="utf-8"))
out["summary"] = s
json.dump(out, open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n汇总:", s)
