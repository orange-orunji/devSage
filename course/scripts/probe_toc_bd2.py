# -*- coding: utf-8 -*-
"""从 probe 渲染图检测红色标题所在页，生成 TOC 条目 JSON。"""
import glob
import json

from docx import Document
from PIL import Image

PROBE_DOCX = r"D:\课设\probe_bd2.docx"
RENDER = r"D:\课设\_render\pb3\page-*.png"
OUT = r"D:\课设\_lib\toc_bd2.json"
OFFSET = 2  # 正文第 1 页 = 物理第 3 页


def bands_of(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    rows = []
    for y in range(h):
        cnt = 0
        for x in range(0, min(640, w), 2):
            r, g, b = px[x, y]
            if r > 130 and g < 110 and b < 110:
                cnt += 1
        if cnt > 3:
            rows.append(y)
    if not rows:
        return []
    out, cur = [], [rows[0]]
    for y in rows[1:]:
        if y - cur[-1] <= 6:
            cur.append(y)
        else:
            out.append((cur[0], cur[-1]))
            cur = [y]
    out.append((cur[0], cur[-1]))
    return out


detected = []
files = sorted(glob.glob(RENDER))
for idx, f in enumerate(files, start=1):
    if idx == 1:
        continue
    for top, bot in bands_of(f):
        detected.append({"page": idx, "y": top, "h": bot - top + 1})

doc = Document(PROBE_DOCX)
heads = []
for p in doc.paragraphs:
    s = p.style.name if p.style else ""
    t = p.text.strip()
    if not t:
        continue
    if s in ("Heading 1", "Heading 2", "Heading1", "Heading2"):
        heads.append((1 if s.endswith("1") else 2, t))

print("文档标题 %d 个，检出红条 %d 个" % (len(heads), len(detected)))

entries = []
ok = True
for i, (level, text) in enumerate(heads):
    if i >= len(detected):
        print("红条不足，缺少:", text)
        ok = False
        break
    d = detected[i]
    guess_level = 1 if d["h"] >= 26 else 2
    if guess_level != level:
        print("层级不符 #%d %s 样式%d 高度%d" % (i, text, level, d["h"]))
        ok = False
    entries.append({"text": text, "page": d["page"] - OFFSET, "level": level, "y": d["y"]})

print("可写入:", ok)
if ok:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print("已写入", OUT)
    for e in entries:
        print("  %s%-28s p%s" % ("  " if e["level"] == 2 else "", e["text"][:26], e["page"]))
else:
    print("未写入，需人工校正")
