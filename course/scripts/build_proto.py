# -*- coding: utf-8 -*-
"""系统详细设计说明书（自建封面 + 目录 + 正文）。"""
import json
import os
import sys

from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

sys.path.insert(0, r"D:\课设\_lib")
import dlib

BASE = r"D:\课设"
OUT = os.path.join(BASE, "智维台", "智维台_界面原型书.docx")
TOC = os.path.join(BASE, "_lib", "toc_proto.json")
IMG = os.path.join(BASE, "图片")
SHOT = os.path.join(BASE, "截图")
PROBE = os.environ.get("PROBE") == "1"
RED = RGBColor(0xC0, 0x00, 0x00)

doc = dlib.new_doc()
counter = dlib.Counter()
HEADS = []


def h1(text):
    par = dlib.h1(doc, text)
    if PROBE:
        par.runs[0].font.color.rgb = RED
    HEADS.append((1, text))


def h2(text):
    par = dlib.h2(doc, text)
    if PROBE:
        par.runs[0].font.color.rgb = RED
    HEADS.append((2, text))


def h3(text):
    par = dlib.h3(doc, text)
    if PROBE:
        par.runs[0].font.color.rgb = RED
    HEADS.append((3, text))


def h(level, text):
    (h1 if level == 1 else h2)(text)


def p(text, indent=True, size=12):
    return dlib.p(doc, text, indent=indent, size=size)


def code(text, size=9):
    return dlib.code(doc, text, size=size)


def table(cap, headers, rows, widths, center=(), size=10.5, first_bold=False, mono_col=None):
    dlib.table(doc, counter, cap, headers, rows, widths, center=center, size=size,
               first_bold=first_bold, mono_col=mono_col)


def figure(path, cap, width=14.2):
    dlib.figure(doc, counter, path, cap, width=width)


# ------------------------------------------------------------------ 封面
doc.add_paragraph()
pp = doc.add_paragraph()
pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
pp.add_run().add_picture(os.path.join(BASE, "_lib", "logo.png"), width=Cm(3.2))
dlib.cover_line(doc, "", 12)
dlib.cover_line(doc, "广州南方学院", 22, space=10, bold=True, east="黑体")
dlib.cover_line(doc, "工学院", 16, space=24, bold=True, east="黑体")
dlib.cover_title(doc, "智维台（OpsDesk）", 26)
dlib.cover_line(doc, "界面原型书", 28, space=12)
dlib.cover_line(doc, "Version 1.0.0", 12, space=24)

TEAM = [("姓名", "学号", "分工", "成绩"),
        ("冯嘉伟", "2420220019", "组长：原型总纲、页面清单与可用性自检", ""),
        ("杨文彬", "2420160092", "问答与工具卡片原型", ""),
        ("刘文源", "2420160053", "上传与入库状态原型", ""),
        ("张琎", "2420160099", "设置页与交互规范", ""),
        ("林景煌", "2410310023", "审批卡片与异常状态设计", "")]
_n0 = len(doc.paragraphs)
dlib.table(doc, dlib.Counter(), "", TEAM[0], TEAM[1:], [3.0, 3.4, 7.2, 2.2], center=(0, 1, 3))
# 去掉封面表格的“表1”题注
for _par in doc.paragraphs[_n0:]:
    if _par.text.startswith("表1") and not _par.text.strip().endswith("备注"):
        if _par.runs and _par.runs[0].text.startswith("表1"):
            _par._p.getparent().remove(_par._p)
        break
dlib.cover_line(doc, "2026 年 11 月 20 日", 14, space=18)
dlib.page_break(doc)

# ------------------------------------------------------------------ 目录
toc_title = doc.add_paragraph()
toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = toc_title.add_run("目　　录")
r.font.size = Pt(18)
r.font.bold = True
r.font.name = "Times New Roman"
r._element.get_or_add_rPr()

entries = []
if not PROBE and os.path.exists(TOC):
    entries = json.load(open(TOC, encoding="utf-8"))

if entries:
    for e in entries:
        par = doc.add_paragraph()
        pf = par.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Pt(0 if e["level"] == 1 else 21)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.5
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        tabs = par.paragraph_format.tab_stops
        tabs.add_tab_stop(Cm(14.6), 2, 1)  # RIGHT, DOT leader
        rr = par.add_run(e["text"])
        rr.font.size = Pt(11 if e["level"] == 1 else 10.5)
        rr.font.bold = (e["level"] == 1)
        par.add_run("\t" + str(e["page"]))
else:
    dlib.p(doc, "（目录将在首次打开时自动生成；此处为占位）", indent=False)

dlib.page_break(doc)

# ------------------------------------------------------------------ 正文
g = globals()
src = open(os.path.join(BASE, "_lib", "proto_content.py"), encoding="utf-8").read()
exec(compile(src, "proto_content.py", "exec"), g)

dlib.add_page_numbers(doc)
name = os.path.join(BASE, "probe_proto.docx") if PROBE else OUT
doc.save(name)
if PROBE:
    json.dump([{"text": t, "level": l} for l, t in HEADS],
              open(os.path.join(BASE, "_lib", "heads_proto.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
print("saved:", name, "heads", len(HEADS), "tables", len(doc.tables))
