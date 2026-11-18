# -*- coding: utf-8 -*-
"""一期 2 层数据流图（v2：三列布局，避免连线交叉）。"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片\dfd2.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

W, H = 1180, 760
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
_f = {}

INK, GRAY, LINE = "#1f2937", "#6b7280", "#4a5568"
BLUE, AMBER = "#2b6cb0", "#b7791f"


def F(s):
    if s not in _f:
        _f[s] = ImageFont.truetype(FONT, s)
    return _f[s]


def box(x, y, w, h, text, size=18):
    d.rectangle([x, y, x + w, y + h], fill="white", outline=BLUE, width=3)
    lines = text.split("\n")
    lh = size + 5
    y0 = y + h / 2 - (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        d.text((x + w / 2, y0 + i * lh), ln, font=F(size if i == 0 else size - 4),
               fill=INK if i == 0 else GRAY, anchor="mm")


def store(x, y, w, h, text):
    d.rectangle([x, y, x + w, y + h], fill="#f8fafc", outline=AMBER, width=3)
    d.text((x + w / 2, y + h / 2), text, font=F(16), fill=INK, anchor="mm")


def head(p2, p1):
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    L = 12
    d.polygon([p2, (p2[0] - L * math.cos(ang - 0.4), p2[1] - L * math.sin(ang - 0.4)),
               (p2[0] - L * math.cos(ang + 0.4), p2[1] - L * math.sin(ang + 0.4))], fill=LINE)


def arrow(pts, label="", lx=None, ly=None, dash=False, size=14):
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        if dash:
            total = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            seg, gap, pos = 10, 7, 0.0
            while pos < total:
                e = min(pos + seg, total)
                d.line([(p1[0] + (p2[0] - p1[0]) * pos / total, p1[1] + (p2[1] - p1[1]) * pos / total),
                        (p1[0] + (p2[0] - p1[0]) * e / total, p1[1] + (p2[1] - p1[1]) * e / total)],
                       fill=LINE, width=2)
                pos = e + gap
        else:
            d.line([p1, p2], fill=LINE, width=2)
    head(pts[-1], pts[-2])
    if label:
        mx = lx if lx is not None else (pts[0][0] + pts[-1][0]) / 2
        my = ly if ly is not None else (pts[0][1] + pts[-1][1]) / 2 - 14
        tw = d.textlength(label, font=F(size))
        d.rectangle([mx - tw / 2 - 4, my - 10, mx + tw / 2 + 4, my + 10], fill="white")
        d.text((mx, my), label, font=F(size), fill=GRAY, anchor="mm")


# 系统边界
d.rectangle([270, 40, 920, 720], fill="white", outline="#94a3b8", width=2)
d.text((282, 54), "系统边界：文档入库与检索（一期）", font=F(14), fill="#64748b")

# 外部实体
box(40, 300, 180, 110, "工程师\n（研发人员）", 17)

# 加工
box(300, 70, 220, 86, "4.1\n上传与解析", 18)
box(300, 220, 220, 86, "4.2\n切分与去重", 18)
box(300, 380, 220, 86, "4.3\n向量化与入库（调 Embedding）", 17)
box(300, 560, 220, 86, "4.4\n检索、重排与生成（调 LLM）", 16)

# 数据存储
store(640, 220, 250, 56, "D5 文档元数据")
store(640, 395, 250, 56, "D6 向量库（Chroma）")

# 入库链
arrow([(200, 300), (200, 113), (300, 113)], "文件 + 元数据", 250, 95)
arrow([(410, 156), (410, 220)], "解析文本", 468, 188)
arrow([(410, 306), (410, 380)], "切片", 440, 344)
arrow([(520, 460), (640, 440)], "向量", 580, 468)
arrow([(520, 250), (640, 248)], "文档记录", 580, 228)

# 问答链
arrow([(220, 360), (282, 360), (282, 600), (300, 600)], "提问", 248, 500)
arrow([(300, 624), (180, 624), (180, 410)], "答案 + 引用", 214, 648)
arrow([(765, 451), (765, 700), (410, 700), (410, 646)], "召回片段（Top-5）", 600, 682, dash=True)

d.text((590, 742), "说明：4.1—4.3 为入库链路（异步，HTTP 202 + 任务轮询）；4.4 为问答链路（SSE 流式，答案逐句标注引用）。",
       font=F(13), fill=GRAY, anchor="mm")
img.save(OUT, dpi=(200, 200))
print("saved", OUT, img.size)
