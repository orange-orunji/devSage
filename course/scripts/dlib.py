# -*- coding: utf-8 -*-
"""课设文档共用排版库：封面要素、标题、正文、表格、图注、页码。"""
import copy
import os

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BODY_SZ = 12
LINE = 1.5


def new_doc(top=2.54, bottom=2.54, left=3.17, right=3.17):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(top), Cm(bottom)
    sec.left_margin, sec.right_margin = Cm(left), Cm(right)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(BODY_SZ)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return doc


def set_font(run, size=BODY_SZ, east="宋体", ascii_f="Times New Roman", bold=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = ascii_f
    if color:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), ascii_f)
    rFonts.set(qn("w:hAnsi"), ascii_f)
    rFonts.set(qn("w:eastAsia"), east)


def cover_title(doc, text, size=26):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(10)
    set_font(par.add_run(text), size, east="黑体", ascii_f="Arial", bold=True)
    return par


def cover_line(doc, text, size=14, space=6, bold=False, east="宋体"):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space)
    set_font(par.add_run(text), size, east=east, bold=bold)
    return par


def h1(doc, text):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(14)
    pf.space_after = Pt(8)
    pf.keep_with_next = True
    par.paragraph_format.first_line_indent = Pt(0)
    set_font(par.add_run(text), 16, east="黑体", ascii_f="Arial", bold=True)
    return par


def h2(doc, text):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    par.paragraph_format.first_line_indent = Pt(0)
    set_font(par.add_run(text), 13.5, east="黑体", ascii_f="Arial", bold=True)
    return par


def h3(doc, text):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(2)
    pf.keep_with_next = True
    par.paragraph_format.first_line_indent = Pt(0)
    set_font(par.add_run(text), 12, east="黑体", ascii_f="Arial", bold=True)
    return par


def p(doc, text, indent=True, size=BODY_SZ, space_after=0, align="justify"):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = LINE
    pf.first_line_indent = Pt(size * 2) if indent else Pt(0)
    par.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                     "left": WD_ALIGN_PARAGRAPH.LEFT,
                     "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    set_font(par.add_run(text), size)
    return par


def code(doc, text, size=9):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.0
    pf.first_line_indent = Pt(0)
    pf.left_indent = Pt(18)
    set_font(par.add_run(text), size, ascii_f="Consolas")


class Counter:
    def __init__(self):
        self.fig = 0
        self.tbl = 0


def caption(doc, c, text, kind, size=10.5):
    if kind == "fig":
        c.fig += 1
        label = "图%d  " % c.fig
    else:
        c.tbl += 1
        label = "表%d  " % c.tbl
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(3)
    pf.space_after = Pt(6)
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = (kind == "tbl")
    set_font(par.add_run(label + text), size, east="黑体")
    return par


def _shade(cell, color="E8EDF3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def _borders(t):
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        b.append(el)
    tblPr.append(b)


def _widths(t, widths):
    tblPr = t._tbl.tblPr
    for el in tblPr.findall(qn("w:tblW")):
        tblPr.remove(el)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(sum(widths) * 567)))
    tw.set(qn("w:type"), "dxa")
    tblPr.append(tw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 567)))
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)


def table(doc, c, cap, headers, rows, widths, center=(), size=10.5, first_bold=False, mono_col=None):
    caption(doc, c, cap, "tbl")
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _borders(t)
    _widths(t, widths)
    for j, text in enumerate(headers):
        cell = t.rows[0].cells[j]
        par = cell.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = par.paragraph_format
        pf.space_before = Pt(1)
        pf.space_after = Pt(1)
        pf.line_spacing = 1.0
        set_font(par.add_run(str(text)), size, bold=True)
        _shade(cell)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = t.rows[i].cells[j]
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER if j in center else WD_ALIGN_PARAGRAPH.LEFT
            pf = par.paragraph_format
            pf.space_before = Pt(1)
            pf.space_after = Pt(1)
            pf.line_spacing = 1.0
            r = par.add_run(str(val))
            if mono_col is not None and j == mono_col:
                set_font(r, 8.5, ascii_f="Consolas")
            else:
                set_font(r, size, bold=(first_bold and j == 0))
    for ri, row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        if ri < len(t.rows) - 1:
            for cell in row.cells:
                for par in cell.paragraphs:
                    par.paragraph_format.keep_with_next = True
    gap = doc.add_paragraph()
    gap.paragraph_format.space_before = Pt(0)
    gap.paragraph_format.space_after = Pt(0)
    gap.paragraph_format.line_spacing = Pt(6)
    set_font(gap.add_run(""), 6)
    return t


def figure(doc, c, path, cap, width=14.4):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(0)
    par.add_run().add_picture(path, width=Cm(width))
    caption(doc, c, cap, "fig")


def add_page_numbers(doc):
    sec = doc.sections[0]
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.text = ""
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "21")
    rpr.append(sz)

    def run(child):
        r = OxmlElement("w:r")
        r.append(copy.deepcopy(rpr))
        r.append(child)
        return r

    for tag, typ in (("w:fldChar", "begin"),):
        el = OxmlElement(tag)
        el.set(qn("w:fldCharType"), typ)
        fp._p.append(run(el))
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " PAGE "
    fp._p.append(run(it))
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    fp._p.append(run(sep))
    t = OxmlElement("w:t")
    t.text = "1"
    fp._p.append(run(t))
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    fp._p.append(run(end))


def page_break(doc):
    from docx.enum.text import WD_BREAK
    par = doc.add_paragraph()
    par.add_run().add_break(WD_BREAK.PAGE)
