# -*- coding: utf-8 -*-
"""界面原型线框图：登录、工作台、审批卡片、会话操作、设置、上传状态。"""
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片"
os.makedirs(OUT, exist_ok=True)
_f = {}

INK, GRAY, LINE = "#1f2937", "#8a94a6", "#4a5568"
FILL, FILL2, ACCENT = "#eceff3", "#f7f8fa", "#2b6cb0"


def F(s):
    if s not in _f:
        _f[s] = ImageFont.truetype(FONT, s)
    return _f[s]


class W:
    def __init__(self, w, h, title=""):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h), "white")
        self.d = ImageDraw.Draw(self.img)
        if title:
            self.t(w / 2, 26, title, 19)

    def t(self, x, y, s, size=14, fill=INK, anchor="mm"):
        self.d.text((x, y), s, font=F(size), fill=fill, anchor=anchor)

    def frame(self, x, y, w, h, label=""):
        self.d.rectangle([x, y, x + w, y + h], outline=LINE, width=2)
        self.d.rectangle([x, y, x + w, y + 34], fill=FILL, outline=LINE, width=2)
        for i in range(3):
            cx = x + 18 + i * 18
            self.d.ellipse([cx - 5, y + 12, cx + 5, y + 22], outline=GRAY, width=2)
        if label:
            self.t(x + w / 2, y + 17, label, 13, GRAY)

    def box(self, x, y, w, h, label="", size=13, fill=None, dash=False, color=LINE, sub=""):
        if fill:
            self.d.rectangle([x, y, x + w, y + h], fill=fill, outline=color, width=2)
        elif dash:
            for px in range(int(x), int(x + w), 12):
                self.d.line([(px, y), (min(px + 6, x + w), y)], fill=color, width=2)
                self.d.line([(px, y + h), (min(px + 6, x + w), y + h)], fill=color, width=2)
            for py in range(int(y), int(y + h), 12):
                self.d.line([(x, py), (x, min(py + 6, y + h))], fill=color, width=2)
                self.d.line([(x + w, py), (x + w, min(py + 6, y + h))], fill=color, width=2)
        else:
            self.d.rectangle([x, y, x + w, y + h], outline=color, width=2)
        if label:
            self.t(x + w / 2, y + h / 2 - (8 if sub else 0), label, size)
        if sub:
            self.t(x + w / 2, y + h / 2 + 12, sub, size - 3, GRAY)

    def btn(self, x, y, w, h, label, primary=True):
        self.d.rectangle([x, y, x + w, y + h], fill=ACCENT if primary else "white",
                         outline=ACCENT, width=2)
        self.t(x + w / 2, y + h / 2, label, 13, "white" if primary else ACCENT)

    def line(self, x1, y1, x2, y2, color=GRAY, wd=1, dash=False):
        if dash:
            import math
            total = math.hypot(x2 - x1, y2 - y1) or 1
            pos = 0
            while pos < total:
                e = min(pos + 8, total)
                self.d.line([(x1 + (x2 - x1) * pos / total, y1 + (y2 - y1) * pos / total),
                             (x1 + (x2 - x1) * e / total, y1 + (y2 - y1) * e / total)], fill=color, width=wd)
                pos = e + 6
        else:
            self.d.line([(x1, y1), (x2, y2)], fill=color, width=wd)

    def note(self, x, y, text, num=None):
        if num:
            self.d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=ACCENT, outline=ACCENT)
            self.t(x, y, str(num), 12, "white")
        else:
            self.t(x, y, text, 12, GRAY, anchor="lm")

    def save(self, name):
        p = os.path.join(OUT, name)
        self.img.save(p, dpi=(200, 200))
        print("saved", p, self.img.size)


def w_login():
    w = W(1000, 620)
    w.frame(60, 70, 880, 500)
    w.d.rectangle([64, 108, 340, 566], fill="#f0f2f5", outline=LINE, width=2)
    w.t(202, 180, "DevSage · 研发智库", 16)
    w.t(202, 214, "面向研发团队的技术知识库 Agent", 11, GRAY)
    for i, s in enumerate(["· 文档检索与智能问答", "· 多轮对话上下文理解", "· 敏感操作人工审批"]):
        w.t(110, 300 + i * 30, s, 12, LINE, anchor="lm")
    w.box(420, 190, 460, 40, "登录 ｜ 注册（分段控件）", 12, fill=FILL2)
    w.t(430, 262, "用户名", 12, LINE, anchor="lm")
    w.box(420, 275, 460, 38, "请输入用户名", 12, dash=True)
    w.t(430, 340, "密码", 12, LINE, anchor="lm")
    w.box(420, 353, 460, 38, "请输入密码", 12, dash=True)
    w.btn(420, 410, 460, 42, "登 录")
    w.t(650, 486, "错误提示区：401 用户名或密码错误", 11, GRAY)
    w.save("wire_login.png")


def w_main():
    w = W(1080, 680)
    w.frame(40, 60, 1000, 560)
    # 左侧栏
    w.d.rectangle([44, 94, 284, 616], fill=FILL2, outline=LINE, width=2)
    w.box(56, 108, 212, 34, "DevSage · 研发智库", 12, fill=FILL)
    w.d.ellipse([58, 156, 86, 184], outline=LINE, width=2)
    w.t(96, 170, "demo_student / 普通用户", 11, LINE, anchor="lm")
    w.box(56, 196, 212, 32, "＋ 新建会话", 12, dash=True)
    w.box(56, 236, 212, 28, "搜索会话…", 11, dash=True)
    w.t(66, 276, "我的会话", 11, GRAY, anchor="lm")
    for i in range(3):
        w.box(56, 286 + i * 34, 212, 30, "会话 %d" % (i + 1), 11, fill="white")
    w.box(56, 520, 212, 40, "上传文档（选择文件）", 11, dash=True)
    # 顶部栏
    w.d.rectangle([290, 94, 1036, 132], fill="white", outline=LINE, width=2)
    w.t(306, 113, "会话标题 / 当前会话 ID", 12, LINE, anchor="lm")
    w.box(880, 100, 140, 24, "RAG 增强检索 ｜ 主题", 10, fill=FILL)
    # 消息区
    w.box(300, 146, 720, 60, "欢迎语：你好，demo_student！我是 DevSage…", 12, dash=True)
    w.box(300, 214, 220, 54, "统计卡 9 文档", 11, fill=FILL2)
    w.box(530, 214, 220, 54, "统计卡 39 切片", 11, fill=FILL2)
    w.box(760, 214, 260, 54, "最近入库 smoke_upload.txt", 11, fill=FILL2)
    w.box(300, 280, 720, 120, "助手回答区（Markdown / 表格 / 代码块 / 引用来源）", 12, dash=True)
    w.box(300, 410, 720, 60, "工具调用卡片：报告已生成 · 下载", 11, dash=True)
    # 输入区
    w.d.rectangle([290, 480, 1036, 616], fill="white", outline=LINE, width=2)
    w.box(306, 492, 120, 26, "快捷指令 ×4", 10, fill=FILL)
    w.box(306, 528, 640, 44, "输入问题，Enter 发送 / Shift+Enter 换行", 11, dash=True)
    w.btn(958, 528, 60, 44, "发送")
    w.save("wire_main.png")


def w_approval():
    w = W(900, 520)
    w.frame(60, 60, 780, 400)
    w.d.rectangle([150, 110, 760, 430], fill="#fbfcfe", outline=ACCENT, width=2)
    w.t(200, 136, "！需要确认的操作", 14, ACCENT, anchor="lm")
    w.line(150, 156, 760, 156, ACCENT, 2)
    for i, (k, v) in enumerate([("动作", "发送邮件"), ("收件人", "team@example.com"),
                                ("主题", "本周研发周报"), ("附件", "report_2026w47.docx")]):
        w.t(176, 182 + i * 34, k, 12, GRAY, anchor="lm")
        w.t(260, 182 + i * 34, v, 12, LINE, anchor="lm")
    w.t(176, 320, "确认后立即执行，取消则放弃本次操作", 11, GRAY, anchor="lm")
    w.btn(500, 350, 110, 38, "确 认")
    w.btn(620, 350, 110, 38, "取 消", False)
    w.t(450, 470, "审批期间输入区锁定；刷新或切会话后按 pending 状态重建卡片", 11, GRAY)
    w.save("wire_approval.png")


def w_settings():
    w = W(900, 560)
    w.frame(60, 60, 780, 440)
    w.d.rectangle([64, 94, 260, 496], fill=FILL2, outline=LINE, width=2)
    for i, s in enumerate(["个人资料", "安全设置", "外观主题", "关于"]):
        w.box(76, 110 + i * 42, 168, 32, s, 12, fill="white" if i == 0 else None)
    w.t(290, 122, "个人资料", 15, INK, anchor="lm")
    w.d.ellipse([290, 150, 350, 210], outline=LINE, width=2)
    w.t(320, 180, "头像", 11, GRAY)
    w.btn(362, 170, 80, 28, "更换", False)
    w.t(290, 240, "显示名 / 用户名", 12, LINE, anchor="lm")
    w.box(290, 252, 420, 36, "demo_student", 12, dash=True)
    w.t(290, 306, "个人简介", 12, LINE, anchor="lm")
    w.box(290, 318, 420, 60, "用于工作台风问候语", 11, dash=True)
    w.t(290, 398, "修改密码：旧密码 / 新密码 / 确认新密码", 12, LINE, anchor="lm")
    w.box(290, 410, 420, 36, "••••••••", 12, dash=True)
    w.btn(290, 456, 120, 34, "保存")
    w.save("wire_settings.png")


def w_upload():
    w = W(980, 480)
    w.frame(40, 60, 900, 360)
    w.box(60, 100, 360, 44, "选择文件 / 拖拽到此处（PDF/DOCX/MD/TXT）", 11, dash=True)
    w.btn(440, 100, 110, 44, "上 传")
    steps = [("1  上传接收", "POST /document/upload → 202 + task_id"),
             ("2  解析切片", "Worker 消费队列：解析 → 切分 → 去重"),
             ("3  向量入库", "写 Chroma（enterprise_knowledge）与元数据"),
             ("4  索引重建", "BM25 全量重建，统计数字刷新")]
    for i, (a, b) in enumerate(steps):
        y = 180 + i * 52
        w.box(60, y, 250, 40, a, 12, fill=FILL2)
        w.line(316, y + 20, 360, y + 20, GRAY, 2, dash=True)
        w.t(372, y + 20, b, 11, GRAY, anchor="lm")
    w.box(60, 392, 200, 30, "进行中 40%", 11, fill=FILL2)
    w.box(280, 392, 200, 30, "完成 9 篇 / 39 切片", 11, fill=FILL2)
    w.box(500, 392, 200, 30, "失败 + 原因（可重试）", 11, fill=FILL2)
    w.t(490, 450, "状态以 task_id 轮询，进度条与统计数字同步更新", 11, GRAY)
    w.save("wire_upload.png")


if __name__ == "__main__":
    w_login()
    w_main()
    w_approval()
    w_settings()
    w_upload()
