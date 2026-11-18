# -*- coding: utf-8 -*-
"""一期 2 层数据流图：文档入库与检索问答。"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片\dfd2.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

W, H = 1400, 780
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
_f = {}


def F(s):
    if s not in _f:
        _f[s] = ImageFont.truetype(FONT, s)
    return _f[s]


INK, GRAY, LINE = "#1f2937", "#6b7280", "#4a5568"
BLUE, AMBER = "#2b6cb0", "#b7791f"


def box(x, y, w, h, text, size=18):
    d.rectangle([x, y, x + w, y + h], fill="white", outline=BLUE, width=3)
    lines = text.split("\n")
    lh = size + 6
    y0 = y + h / 2 - (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        d.text((x + w / 2, y0 + i * lh), ln, font=F(size if i == 0 else size - 3),
               fill=INK if i == 0 else GRAY, anchor="mm")


def store(x, y, w, h, text):
    d.rectangle([x, y, x + w, y + h], fill="#f8fafc", outline=AMBER, width=3)
    d.text((x + w / 2, y + h / 2), text, font=F(16), fill=INK, anchor="mm")


def arrow(pts, label="", lab_dy=-16, size=14):
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=LINE, width=2)
    p1, p2 = pts[-2], pts[-1]
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    L = 12
    d.polygon([p2, (p2[0] - L * math.cos(ang - 0.4), p2[1] - L * math.sin(ang - 0.4)),
               (p2[0] - L * math.cos(ang + 0.4), p2[1] - L * math.sin(ang + 0.4))], fill=LINE)
    if label:
        mx = (pts[0][0] + p2[0]) / 2
        my = (pts[0][1] + p2[1]) / 2 + lab_dy
        tw = d.textlength(label, font=F(size))
        d.rectangle([mx - tw / 2 - 4, my - 10, mx + tw / 2 + 4, my + 10], fill="white")
        d.text((mx, my), label, font=F(size), fill=GRAY, anchor="mm")


# 外部实体
box(30, 210, 190, 74, "工程师\n（研发人员）", 17)
box(30, 470, 190, 74, "Embedding / LLM\n（外部服务）", 15)

# 系统边界
d.rectangle([260, 60, 1080, 720], fill="white", outline="#94a3b8", width=2)
d.text((270, 76), "系统边界：文档入库与检索（一期）", font=F(15), fill="#64748b")

# 加工 4.1 - 4.4
box(320, 140, 230, 92, "4.1\n上传与解析", 19)
box(320, 320, 230, 92, "4.2\n切分与去重", 19)
box(320, 500, 230, 92, "4.3\n向量化与入库", 19)
box(680, 320, 240, 92, "4.4\n检索、重排与生成", 19)

# 数据存储
store(700, 560, 230, 62, "D6 向量库（Chroma）")
store(700, 640, 230, 62, "D5 文档元数据")

# 数据流
arrow([(220, 240), (320, 196)], "文件 + 元数据", -18)
arrow([(435, 232), (435, 320)], "解析文本", -14)
arrow([(435, 412), (435, 500)], "切片", -14)
arrow([(550, 546), (700, 588)], "向量 + 元数据", -16)
arrow([(220, 250), (700, 340)], "提问", -14)
arrow([(700, 400), (220, 300)], "答案 + 引用来源", 16)
arrow([(700, 366), (680, 366)], "召回片段", -14)
arrow([(435, 592), (700, 660)], "文档记录", 16)
arrow([(435, 592), (250, 520)], "向量请求", 18)

d.text((700, 748), "说明：4.1—4.3 为入库链路（异步，HTTP 202 + task 轮询）；4.4 为问答链路（SSE 流式）。",
       font=F(14), fill=GRAY, anchor="mm")
img.save(OUT, dpi=(200, 200))
print("saved", OUT, img.size)
