# -*- coding: utf-8 -*-
"""测试报告插图：用例结果分布、耗时分布。"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片"
_f = {}
INK, GRAY, LINE = "#1f2937", "#6b7280", "#4a5568"
BLUE, GREEN, RED, GREY = "#2b6cb0", "#2f855a", "#c53030", "#94a3b8"


def F(s):
    if s not in _f:
        _f[s] = ImageFont.truetype(FONT, s)
    return _f[s]


def bars(path, title, labels, series, colors, legend, y_unit="条", width=1000, height=520):
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    if title:
        d.text((width / 2, 28), title, font=F(20), fill=INK, anchor="mm")
    left, right, top, bottom = 90, width - 40, 80, height - 90
    maxv = max(max(s) for s in series) or 1
    import math
    step = max(1, math.ceil(maxv / 5))
    for i in range(6):
        y = bottom - (bottom - top) * i / 5
        d.line([(left, y), (right, y)], fill="#e5e7eb", width=1)
        d.text((left - 12, y), "%d" % round(step * i), font=F(13), fill=GRAY, anchor="rm")
    n = len(labels)
    gw = (right - left) / n
    bw = gw / (len(series) + 0.8)
    for i, lab in enumerate(labels):
        x0 = left + i * gw + gw * 0.12
        for si, s in enumerate(series):
            v = s[i]
            h = (bottom - top) * v / (step * 5)
            x = x0 + si * bw
            d.rectangle([x, bottom - h, x + bw * 0.86, bottom], fill=colors[si])
            if v:
                d.text((x + bw * 0.43, bottom - h - 12), str(v), font=F(13), fill=INK, anchor="mm")
        d.text((left + i * gw + gw / 2, bottom + 22), lab, font=F(14), fill=LINE, anchor="mm")
    lx = left
    for i, name in enumerate(legend):
        d.rectangle([lx, height - 44, lx + 14, height - 30], fill=colors[i])
        d.text((lx + 20, height - 37), name, font=F(13), fill=LINE, anchor="lm")
        lx += 26 + len(name) * 14
    img.save(path, dpi=(200, 200))
    print("saved", path, img.size)


data = json.load(open(r"D:\课设\_test\results.json", encoding="utf-8"))
res = data["results"]

mods = ["M1 认证", "M2 会话", "M3 文档", "M4 检索问答", "M5 交付工具", "M6 安全", "基础", "兼容性"]
stat = {m: {"PASS": 0, "FAIL": 0, "BLOCK": 0} for m in mods}
for r in res:
    m = r["module"] if r["module"] in stat else "基础"
    stat[m][r["status"]] += 1

bars(os.path.join(OUT, "test_result.png"), "",
     [m.replace(" ", "\n") for m in mods],
     [[stat[m]["PASS"] for m in mods], [stat[m]["FAIL"] for m in mods], [stat[m]["BLOCK"] for m in mods]],
     [GREEN, RED, GREY], ["通过", "失败", "未执行"], height=560)

lat = [(r["id"], r["ms"]) for r in res if r.get("ms")]
lat.sort(key=lambda x: -x[1])
top = lat[:10]
bars(os.path.join(OUT, "test_latency.png"), "",
     [x[0] for x in top], [[x[1] for x in top]], [BLUE], ["耗时"], height=520)
