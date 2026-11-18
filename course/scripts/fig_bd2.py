# -*- coding: utf-8 -*-
"""概要设计插图：总体架构、部署视图、模块结构。"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片"
os.makedirs(OUT, exist_ok=True)
_f = {}
INK, GRAY, LINE = "#1f2937", "#6b7280", "#4a5568"
BLUE, BLUE_BG = "#2b6cb0", "#e8f0fa"
GREEN, GREEN_BG = "#2f855a", "#e6f4ea"
AMBER, AMBER_BG = "#b7791f", "#fdf3e2"
GREY, GREY_BG = "#94a3b8", "#f3f4f6"


def F(s):
    if s not in _f:
        _f[s] = ImageFont.truetype(FONT, s)
    return _f[s]


class C:
    def __init__(self, w, h, bg="white"):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), bg)
        self.d = ImageDraw.Draw(self.img)

    def t(self, x, y, s, size=18, fill=INK, anchor="mm"):
        self.d.text((x, y), s, font=F(size), fill=fill, anchor=anchor)

    def box(self, x, y, w, h, text, fill="white", outline=BLUE, size=17, r=0, wd=3, color=INK):
        if r:
            self.d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=outline, width=wd)
        else:
            self.d.rectangle([x, y, x + w, y + h], fill=fill, outline=outline, width=wd)
        lines = text.split("\n")
        lh = size + 5
        y0 = y + h / 2 - (len(lines) - 1) * lh / 2
        for i, ln in enumerate(lines):
            self.t(x + w / 2, y0 + i * lh, ln, size if i == 0 else size - 4,
                   color if i == 0 else GRAY)

    def band(self, x, y, w, h, label, fill=GREY_BG):
        self.d.rectangle([x, y, x + w, y + h], fill=fill, outline="#cbd5e1", width=2)
        self.t(x + 46, y + h / 2, label, 17, GRAY)

    def arrow(self, pts, label="", lx=None, ly=None, dash=False, size=14, color=LINE):
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            if dash:
                total = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1
                seg, gap, pos = 9, 6, 0.0
                while pos < total:
                    e = min(pos + seg, total)
                    self.d.line([(p1[0] + (p2[0] - p1[0]) * pos / total, p1[1] + (p2[1] - p1[1]) * pos / total),
                                 (p1[0] + (p2[0] - p1[0]) * e / total, p1[1] + (p2[1] - p1[1]) * e / total)],
                                fill=color, width=2)
                    pos = e + gap
            else:
                self.d.line([p1, p2], fill=color, width=2)
        ang = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
        L = 11
        self.d.polygon([pts[-1],
                        (pts[-1][0] - L * math.cos(ang - 0.42), pts[-1][1] - L * math.sin(ang - 0.42)),
                        (pts[-1][0] - L * math.cos(ang + 0.42), pts[-1][1] - L * math.sin(ang + 0.42))], fill=color)
        if label:
            mx = lx if lx is not None else (pts[0][0] + pts[-1][0]) / 2
            my = ly if ly is not None else (pts[0][1] + pts[-1][1]) / 2 - 14
            tw = self.d.textlength(label, font=F(size))
            self.d.rectangle([mx - tw / 2 - 4, my - 10, mx + tw / 2 + 4, my + 10], fill="white")
            self.t(mx, my, label, size, GRAY)

    def save(self, name):
        p = os.path.join(OUT, name)
        self.img.save(p, dpi=(200, 200))
        print("saved", p, self.img.size)


def fig_arch():
    c = C(1320, 900)
    c.t(660, 34, "系统总体架构（一期）", 22)
    layers = [
        ("表现层", 70, ["对话工作台\nVue3 + Vite", "会话侧栏\n新建/切换/重命名", "审批卡片\n确认 / 驳回", "设置与资料\n头像 / 改密"]),
        ("接口层", 210, ["REST\n/auth /document", "SSE 流式\n/chat/stream", "JWT 鉴权\nBearer Token", "限流与校验\nslowapi / Pydantic"]),
        ("应用服务层", 350, ["认证服务\nAuthService", "文档服务\nDocService", "检索问答\nRagService", "交付工具\nTools", "会话记忆\nSessionService"]),
        ("能力层", 490, ["三阶检索\nHyDE→BM25→Rerank", "意图路由\n正则→IDF→语义", "LangGraph\nStateGraph", "Tool Calling\n7 个工具", "人工审批\ninterrupt/resume"]),
        ("基础设施层", 630, ["SQLite\napp.db", "Chroma\n向量库", "Redis\n缓存/临时文件", "RabbitMQ\n异步任务", "模型 API\nLLM/Embedding"]),
    ]
    for name, y, items in layers:
        c.band(40, y, 1240, 110, name)
        n = len(items)
        gap = 12
        w = (1085 - gap * (n - 1)) / n
        for i, it in enumerate(items):
            fill, outline = "white", BLUE
            if name == "基础设施层":
                fill, outline = GREY_BG, GREY
            c.box(176 + i * (w + gap), y + 14, w, 82, it, fill=fill, outline=outline)
    for y in (180, 320, 460, 600):
        c.arrow([(1050, y), (1050, y + 30)], color=LINE)
    c.t(660, 872, "说明：上层仅通过下层暴露的接口调用；能力层不含业务状态，状态由应用服务层与 LangGraph 检查点维护。", 14, GRAY)
    c.save("arch.png")


def fig_deploy():
    c = C(1320, 720)
    c.t(660, 30, "部署与网络视图（Docker Compose）", 22)
    c.d.rectangle([40, 70, 330, 650], fill="#fbfcfd", outline="#cbd5e1", width=2)
    c.t(185, 96, "用户侧", 17, GRAY)
    c.d.rectangle([370, 70, 950, 650], fill="#f8fbf8", outline=GREEN, width=2)
    c.t(660, 96, "企业内网 / Docker 主机", 17, GREEN)
    c.d.rectangle([985, 70, 1280, 650], fill="#fbfcfd", outline="#cbd5e1", width=2)
    c.t(1132, 96, "外部服务", 17, GRAY)

    c.box(70, 200, 270, 90, "浏览器\nChrome / Edge", fill=BLUE_BG, outline=BLUE)
    c.box(70, 380, 270, 90, "局域网访问\nhttp://内网IP:9000", fill="white", outline=GREY)

    c.box(410, 170, 250, 110, "api 容器\nUvicorn + FastAPI\n托管 Vue 构建产物", fill=GREEN_BG, outline=GREEN)
    c.box(410, 380, 250, 84, "redis 容器\n缓存 / 上传临时文件", fill=GREEN_BG, outline=GREEN)
    c.box(410, 500, 250, 84, "rabbitmq 容器\n文档异步解析队列", fill=GREEN_BG, outline=GREEN)
    c.box(700, 380, 220, 84, "数据卷\napp.db / chroma / uploads", fill=GREY_BG, outline=GREY)

    c.box(1030, 200, 230, 100, "LLM 与 Embedding\nOpenAI 兼容 API", fill=AMBER_BG, outline=AMBER)
    c.box(1030, 360, 230, 90, "SMTP 邮箱\nQQ / 企业邮箱", fill=AMBER_BG, outline=AMBER)
    c.box(1030, 510, 230, 90, "博查联网搜索\n兜底检索", fill=AMBER_BG, outline=AMBER)

    c.arrow([(340, 250), (410, 230)], "HTTPS", 375, 226)
    c.arrow([(660, 280), (660, 380)], "会话/缓存", 588, 330)
    c.arrow([(660, 464), (660, 500)], "任务投递", 730, 482)
    c.arrow([(660, 380), (700, 400)], "", None, None, True)
    c.arrow([(660, 240), (1030, 240)], "HTTPS", 845, 218)
    c.arrow([(660, 292), (980, 292), (1030, 400)], "SMTP", 760, 272)
    c.arrow([(660, 330), (980, 330), (1030, 540)], "HTTPS", 860, 310, True)
    c.t(660, 690, "说明：仅 api 容器对外暴露 9000 端口；数据卷挂载 app/data，保证重启后会话记忆、向量库与上传文件不丢。", 14, GRAY)
    c.save("deploy.png")


def fig_module():
    c = C(1320, 640)
    c.t(660, 30, "系统模块结构（一期六模块）", 22)
    c.box(510, 70, 300, 66, "智维台（一期）", fill=BLUE_BG, outline=BLUE, size=19)
    mods = [
        ("M1 认证与用户", ["注册 / 登录", "JWT 鉴权", "资料与头像", "改密"]),
        ("M2 会话与记忆", ["新建 / 切换", "重命名 / 删除", "多轮记忆", "检查点持久化"]),
        ("M3 文档与知识库", ["上传解析", "切片去重", "向量入库", "统计与删除"]),
        ("M4 检索问答", ["意图路由", "混合召回", "重排与生成", "引用与联网"]),
        ("M5 交付工具", ["报告生成", "格式转换", "邮件发送", "文件下载"]),
        ("M6 审批与安全", ["人工审批", "中断恢复", "限流防呆", "操作留痕"]),
    ]
    x0, gap = 40, 14
    bw = (1240 - gap * 5) / 6
    for i, (name, subs) in enumerate(mods):
        x = x0 + i * (bw + gap)
        cx = x + bw / 2
        c.arrow([(660, 136), (660, 160), (cx, 160), (cx, 186)] if abs(cx - 660) > 1 else [(660, 136), (660, 186)],
                color=LINE, size=12)
        c.box(x, 186, bw, 60, name, fill=GREEN_BG, outline=GREEN, size=17)
        for j, s in enumerate(subs):
            y = 268 + j * 62
            c.box(x + 4, y, bw - 8, 52, s, fill="white", outline=GREY, size=15)
            c.arrow([(cx, y - 10), (cx, y)], color=GREY, size=10)
    c.t(660, 612, "说明：六个模块对应一期五项能力域（认证/文档/检索/交付/会话）+ 安全与审批；模块间只经 application 层接口调用。", 14, GRAY)
    c.save("module.png")


if __name__ == "__main__":
    fig_arch()
    fig_deploy()
    fig_module()
