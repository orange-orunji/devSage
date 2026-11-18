# -*- coding: utf-8 -*-
"""详细设计插图：抽象类视图、问答时序图、包视图、类/接口视图。"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
MONO = r"C:\Windows\Fonts\consola.ttf"
OUT = r"D:\课设\图片"
os.makedirs(OUT, exist_ok=True)
_f = {}
INK, GRAY, LINE = "#1f2937", "#6b7280", "#4a5568"
BLUE, BLUE_BG = "#2b6cb0", "#e8f0fa"
GREEN, GREEN_BG = "#2f855a", "#e6f4ea"
AMBER, AMBER_BG = "#b7791f", "#fdf3e2"
GREY, GREY_BG = "#94a3b8", "#f3f4f6"


def F(s, mono=False):
    key = (s, mono)
    if key not in _f:
        _f[key] = ImageFont.truetype(MONO if mono else FONT, s)
    return _f[key]


class C:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), "white")
        self.d = ImageDraw.Draw(self.img)

    def t(self, x, y, s, size=18, fill=INK, anchor="mm", mono=False):
        self.d.text((x, y), s, font=F(size, mono), fill=fill, anchor=anchor)

    def _head(self, p2, p1):
        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        L = 11
        self.d.polygon([p2, (p2[0] - L * math.cos(ang - 0.42), p2[1] - L * math.sin(ang - 0.42)),
                        (p2[0] - L * math.cos(ang + 0.42), p2[1] - L * math.sin(ang + 0.42))], fill=LINE)

    def line(self, pts, dash=False, color=LINE, wdt=2):
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            if dash:
                total = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
                seg, gap, pos = 9, 6, 0.0
                while pos < total:
                    e = min(pos + seg, total)
                    self.d.line([(p1[0] + (p2[0] - p1[0]) * pos / total, p1[1] + (p2[1] - p1[1]) * pos / total),
                                 (p1[0] + (p2[0] - p1[0]) * e / total, p1[1] + (p2[1] - p1[1]) * e / total)],
                                fill=color, width=wdt)
                    pos = e + gap
            else:
                self.d.line([p1, p2], fill=color, width=wdt)

    def arrow(self, pts, label="", lx=None, ly=None, dash=False, size=13):
        self.line(pts, dash)
        self._head(pts[-1], pts[-2])
        if label:
            mx = lx if lx is not None else (pts[0][0] + pts[-1][0]) / 2
            my = ly if ly is not None else (pts[0][1] + pts[-1][1]) / 2 - 12
            tw = self.d.textlength(label, font=F(size))
            self.d.rectangle([mx - tw / 2 - 4, my - 9, mx + tw / 2 + 4, my + 9], fill="white")
            self.t(mx, my, label, size, GRAY)

    def cls(self, x, y, w, title, attrs, methods, fill=BLUE_BG, outline=BLUE, size=15, stereo=None):
        head = 40 + (22 if stereo else 0)
        ah = len(attrs) * 22 + 8
        mh = len(methods) * 22 + 8
        h = head + ah + mh
        self.d.rectangle([x, y, x + w, y + h], fill="white", outline=outline, width=2)
        self.d.rectangle([x, y, x + w, y + head], fill=fill, outline=outline, width=2)
        yy = y + 18
        if stereo:
            self.t(x + w / 2, yy, stereo, 12, GRAY)
            yy += 20
        self.t(x + w / 2, yy + 2, title, size + 1)
        self.d.line([(x, y + head), (x + w, y + head)], fill=outline, width=2)
        yy = y + head + 6
        for a in attrs:
            self.t(x + 10, yy + 7, a, size - 2, INK, anchor="lm", mono=True)
            yy += 22
        self.d.line([(x, yy + 2), (x + w, yy + 2)], fill=outline, width=1)
        yy += 6
        for m in methods:
            self.t(x + 10, yy + 7, m, size - 2, "#1f4e79", anchor="lm", mono=True)
            yy += 22
        return h

    def save(self, name):
        p = os.path.join(OUT, name)
        self.img.save(p, dpi=(200, 200))
        print("saved", p, self.img.size)


def fig_abstract():
    c = C(1400, 760)
    c.t(700, 30, "抽象类视图（接口与领域实体）", 22)
    ifs = [
        ("AuthService", ["+register(u, p) -> Token", "+login(u, p) -> Token", "+me(token) -> User", "+change_password(old, new)"], BLUE_BG, BLUE),
        ("DocService", ["+upload(file, uid) -> task_id", "+status(task_id) -> TaskState", "+stats() -> DocStats", "+delete(doc_id) -> bool"], GREEN_BG, GREEN),
        ("RagService", ["+ask(q, sid) -> Stream", "+retrieve(q) -> list[Chunk]", "+route(q) -> Intent", "- _build_prompt(chunks)"], GREEN_BG, GREEN),
        ("ToolRegistry", ["+register(name, fn)", "+dispatch(name, args)", "+list_tools() -> list", "+interrupt_if_sensitive()"], AMBER_BG, AMBER),
        ("StateGraph", ["+route(state) -> node", "+retrieve_node(state)", "+tool_node(state)", "+interrupt(resume)"], AMBER_BG, AMBER),
    ]
    ent = [("User", ["id", "username", "hashed_pwd"]), ("Session", ["session_id", "user_id", "title"]),
           ("Message", ["message_id", "role", "content"]), ("Document", ["doc_id", "name", "chunk_count"]),
           ("Chunk", ["chunk_id", "doc_id", "text"])]
    w, gap, x0 = 248, 20, 25
    for i, (name, ms, fill, outline) in enumerate(ifs):
        c.cls(x0 + i * (w + gap), 80, w, name, [], ms, fill=fill, outline=outline, size=14, stereo="«interface»")
        c.arrow([(x0 + i * (w + gap) + w / 2, 246), (x0 + i * (w + gap) + w / 2, 462)],
                "依赖" if i == 2 else "", dash=True)
    for i, (name, attrs) in enumerate(ent):
        c.cls(x0 + i * (w + gap), 470, w, name, attrs, [], fill=GREY_BG, outline=GREY, size=14)
    c.t(700, 700, "说明：接口定义在 services 层（蓝：平台能力，绿：知识能力，橙：编排能力），实现类只依赖 domain 实体，持久化与外部调用经 adapters 注入。", 14, GRAY)
    c.save("dd_abstract.png")


def fig_seq():
    c = C(1400, 900)
    c.t(700, 28, "问答链路时序图（/api/chat/stream）", 22)
    parts = [("浏览器", 90, BLUE), ("chat 路由", 330, BLUE), ("状态图", 570, AMBER),
             ("检索服务", 810, GREEN), ("模型 API", 1050, AMBER), ("存储", 1290, GREY)]
    for name, x, col in parts:
        c.d.rectangle([x - 70, 70, x + 70, 116], fill="white", outline=col, width=2)
        c.t(x, 93, name, 15)
        c.line([(x, 116), (x, 830)], color="#cbd5e1", wdt=1)

    steps = [
        (1, 90, 330, "POST /chat/stream {question, session_id}", 150),
        (2, 330, 570, "invoke(state)", 178),
        (3, 570, 570, "route(question) -> 知识类", 206),
        (4, 570, 810, "retrieve(q, top_k=5)", 234),
        (5, 810, 810, "HyDE 扩展 → BM25 + 向量 → RRF 融合", 262),
        (6, 810, 1050, "rerank(candidates)", 290),
        (7, 810, 570, "list[Chunk] (含来源元数据)", 318),
        (8, 570, 1050, "generate(prompt, chunks)", 346),
        (9, 1050, 570, "token 流", 374),
        (10, 570, 570, "tool call -> 执行工具", 402),
        (11, 570, 330, "SSE: delta / citation", 430),
        (12, 330, 90, "SSE 逐帧推送", 458),
        (13, 570, 1290, "save_checkpoint(state)", 486),
        (14, 570, 330, "done", 514),
    ]
    for idx, x1, x2, label, y in steps:
        if x1 == x2:
            c.d.rectangle([x1 - 5, y - 16, x1 + 5, y + 16], fill="#e2e8f0", outline="#94a3b8")
            c.arrow([(x1 + 5, y - 10), (x1 + 46, y - 10), (x1 + 46, y + 10), (x1 + 8, y + 10)], "")
            _tw = c.d.textlength(label, font=F(14))
            c.d.rectangle([x1 - 14 - _tw - 4, y - 10, x1 - 10, y + 10], fill="white")
            c.t(x1 - 14, y + 2, label, 14, INK, anchor="rm")
            continue
        c.arrow([(x1 + (8 if x2 > x1 else -8), y), (x2 - (10 if x2 > x1 else -10), y)], label,
                (x1 + x2) / 2, y - 14)
    c.t(700, 862, "说明：第 10 步仅当模型返回 tool_calls 时发生（报告生成/邮件发送）；邮件发送在此处 interrupt，等待人工审批后 resume。",
        14, GRAY)
    c.save("dd_seq.png")


def fig_pkg():
    c = C(1300, 760)
    c.t(650, 30, "构件 / 包视图（分层单体）", 22)
    pk = [
        ("api", 60, 110, 560, ["chat.py / document.py / auth.py", "SSE encode / validate / auth"], BLUE_BG, BLUE),
        ("services", 60, 300, 560, ["auth_service / doc_service", "rag_service / session_service", "tool_registry"], GREEN_BG, GREEN),
        ("domain", 60, 520, 560, ["user / session / message", "document / chunk", "intent / citation"], GREY_BG, GREY),
        ("adapters", 700, 300, 520, ["repository_sqlite", "vector_store(chroma)", "llm_gateway / mailer", "queue(rabbitmq) / cache(redis)"], AMBER_BG, AMBER),
        ("common", 700, 520, 520, ["settings / logging", "errors / retry", "security(jwt)"], GREY_BG, GREY),
    ]
    for name, x, y, w, lines, fill, outline in pk:
        h = 54 + len(lines) * 24
        c.d.rectangle([x, y, x + w, y + h], fill="white", outline=outline, width=2)
        c.d.rectangle([x, y, x + w, y + 40], fill=fill, outline=outline, width=2)
        c.t(x + w / 2, y + 20, name, 18)
        yy = y + 52
        for ln in lines:
            c.t(x + 16, yy + 8, ln, 14, INK, anchor="lm", mono=True)
            yy += 24
    c.arrow([(340, 260), (340, 300)], "调用", 380, 280)
    c.arrow([(340, 450), (340, 520)], "依赖实体", 400, 485)
    c.arrow([(620, 340), (700, 340)], "实现接口", 660, 320)
    c.arrow([(620, 400), (700, 480)], "注入", 665, 450)
    c.t(650, 720, "依赖方向单向：api → services → domain，adapters 实现 services 定义的端口，common 被各层引用；禁止反向 import。",
        14, GRAY)
    c.save("dd_pkg.png")


def fig_class():
    c = C(1400, 860)
    c.t(700, 28, "类 / 接口视图（核心实现类）", 22)
    c.cls(40, 70, 320, "ChatRouter", ["limiter: Limiter", "graph: StateGraph"], [
        "@POST /stream", "@GET /sessions", "@POST /resume",
        "- _sse(event) -> str",
    ])
    c.cls(40, 330, 320, "RagService", ["retriever: HybridRetriever", "reranker: Reranker"], [
        "+ask(q, sid) -> AsyncIterator",
        "+retrieve(q) -> list[Chunk]",
        "- _build_prompt(chunks)",
    ], fill=GREEN_BG, outline=GREEN)
    c.cls(40, 610, 320, "DocService", ["store: VectorStore", "queue: TaskQueue"], [
        "+upload(file, uid) -> str",
        "+handle_task(task_id)",
        "- _split(text) -> list[str]",
    ], fill=GREEN_BG, outline=GREEN)
    c.cls(500, 70, 340, "HybridRetriever", ["bm25: BM25Index", "store: VectorStore"], [
        "+search(q, k) -> list[Chunk]",
        "- _hyde(q) -> str",
        "- _rrf(a, b) -> list[Chunk]",
    ], fill=AMBER_BG, outline=AMBER)
    c.cls(500, 330, 340, "SessionService", ["repo: SessionRepo", "cp: Checkpointer"], [
        "+list(uid) -> list[Session]",
        "+rename(sid, title)",
        "+history(sid) -> list[Message]",
    ])
    c.cls(500, 560, 340, "ToolRegistry", ["_tools: dict[str, Callable]"], [
        "+register(name, fn)",
        "+dispatch(name, **kw)",
        "+interrupt_if_sensitive(name)",
    ], fill=AMBER_BG, outline=AMBER)
    c.cls(950, 70, 400, "UserRepo (adapter)", ["engine: Engine", "SessionLocal"], [
        "+by_name(u) -> User | None",
        "+create(u, pwd) -> User",
        "+update_profile(uid, **kw)",
    ], fill=GREY_BG, outline=GREY)
    c.cls(950, 330, 400, "VectorStore (adapter)", ["client: chromadb.Client", "col: Collection"], [
        "+add(ids, docs, metas, embs)",
        "+query(vec, k) -> list[Chunk]",
        "+delete(doc_id)",
    ], fill=GREY_BG, outline=GREY)
    c.cls(950, 560, 400, "LlmGateway (adapter)", ["base_url / api_key", "model"], [
        "+chat(messages) -> str",
        "+astream(messages) -> AsyncIterator",
        "+embed(texts) -> list[vec]",
    ], fill=GREY_BG, outline=GREY)

    c.arrow([(360, 200), (500, 160)], "组合", 430, 168)
    c.arrow([(360, 380), (500, 180)], "使用", 430, 300, dash=True)
    c.arrow([(360, 660), (500, 640)], "使用", 430, 640, dash=True)
    c.arrow([(840, 240), (950, 200)], "调用", 895, 210)
    c.arrow([(840, 600), (950, 620)], "调用", 895, 600)
    c.arrow([(840, 400), (950, 380)], "调用", 895, 380, dash=True)
    c.t(700, 830, "说明：适配器（灰）实现端口，业务类（蓝/绿/橙）只依赖接口；更换模型或向量库只需替换适配器。", 14, GRAY)
    c.save("dd_class.png")


if __name__ == "__main__":
    fig_abstract()
    fig_seq()
    fig_pkg()
    fig_class()
