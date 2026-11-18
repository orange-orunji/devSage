# -*- coding: utf-8 -*-
"""阶段一：把 SRS 改成“一期已实现 + 二期规划”口径。"""
import copy
import os
import sys

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"D:\课设\智维台\软件需求规格说明书_智维台.docx"
doc = Document(SRC)

STATUS = {
    "FR-01": "已实现", "FR-02": "部分实现", "FR-03": "已实现", "FR-04": "已实现",
    "FR-05": "已实现", "FR-06": "已实现", "FR-07": "二期", "FR-08": "二期",
    "FR-09": "二期", "FR-10": "部分实现", "FR-11": "已实现", "FR-12": "部分实现",
    "FR-13": "已实现", "FR-14": "部分实现", "FR-15": "部分实现", "FR-16": "已实现",
}
NOTE = {
    "FR-02": "仅普通用户，RBAC 为演示接口",
    "FR-10": "有检索与多步建议，未与工单挂靠",
    "FR-12": "入库即沉淀，无二级审核",
    "FR-14": "仅文档/切片统计",
    "FR-15": "有日志文件，无查询界面",
    "FR-07": "无工单实体", "FR-08": "无状态机", "FR-09": "无分派逻辑",
}


def set_text(par, text):
    runs = par.runs
    if not runs:
        par.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


def find_par(keyword, start=0):
    for i, p in enumerate(doc.paragraphs):
        if i >= start and keyword in p.text:
            return i, p
    return None, None


# ------------------------------------------------------------ 1. 改正文口径
edits = [
    ("本系统覆盖企业 IT 服务台",
     "第一期交付覆盖五个能力域：认证与用户隔离、文档与知识库管理、智能检索与问答、交付（报告生成/格式转换/邮件发送）、会话与记忆；"
     "工单管理、自动分派、指标看板等原规划能力列入第二期，本文档在相应位置标注“二期”，需求与实现的对应关系见表 3 的“实现状态”列。"),
    ("系统以工单为主线组织功能",
     "第一期以“知识与交付”为主线组织功能：用户经认证进入工作台，可检索知识库提问并得到带来源的答案；"
     "需要产出物时，由智能体调用报告生成、格式转换或邮件发送工具完成交付，敏感动作走人工审批；文档上传后异步解析入库，形成可检索的知识。"
     "工单建单、分派与状态流转属二期规划，一期不涉及。"),
    ("依据调研结论与用例分析，整理出 16 条功能需求",
     "依据调研结论与代码实现，整理出 16 条功能需求，编号、描述与验收标准如表 3 所示。优先级 P0 为必须实现，P1 为应当实现，P2 为二期规划；"
     "“实现状态”列标注该需求在当前版本（仓库 devSage，master@36d1d48）中的落地情况：已实现 8 条、部分实现 5 条、二期 3 条。"),
    ("本节采用结构化分析方法，自顶向下对系统进行分解。顶层图确定系统边界",
     "本节采用结构化分析方法，自顶向下对系统进行分解。顶层图确定系统边界与外部实体，1 层图划分主要业务加工与数据存储；"
     "2 层图在一期以“文档入库与检索”为展开对象（见附录 A 图 A-1），原“工单管理”的 2 层分解（图 4）保留作为二期设计参考。"),
    ("2 层数据流图对 1 层图中的加工 4“工单管理”进行细化",
     "2 层数据流图对 1 层图中的加工 4“工单管理”进行细化，分解为 4.1 要素抽取与校验、4.2 工单生成与去重、4.3 自动分派、4.4 状态流转与结案。"
     "该图为二期（工单域）设计参考，一期对应的 2 层分解见附录 A。"),
    ("图 4  2 层数据流图（加工 4 展开）", "图 4  2 层数据流图（加工 4 工单管理展开，二期）"),
    ("（1）核心任务（提问、建单、查看工单）在主界面三次点击内可达",
     "（1）核心任务（提问、上传文档、发起交付）在主界面三次点击内可达；"),
]
for key, new in edits:
    i, p = find_par(key)
    if p is None:
        print("未找到段落:", key)
        continue
    set_text(p, new)
    print("已改段:", key[:22])

# ------------------------------------------------------------ 2. 重建表 3（加“实现状态”列）
old = None
for _t in doc.tables:
    _h = [c.text.strip() for c in _t.rows[0].cells]
    if "需求描述" in _h and "验收标准" in _h:
        old = _t
        break
assert old is not None, "未找到功能需求表"
print("目标表：%d 行 %d 列" % (len(old.rows), len(old.columns)))
rows = len(old.rows)
new_tbl = copy.deepcopy(old._tbl)
old._tbl.addprevious(new_tbl)
old._tbl.getparent().remove(old._tbl)

from docx.table import Table
t = Table(new_tbl, doc)

# 扩展 tblGrid（否则固定布局下第 6 列不显示）
grid = t._tbl.find(qn("w:tblGrid"))
cols = grid.findall(qn("w:gridCol"))
newcol = copy.deepcopy(cols[-1])
cols[-1].addnext(newcol)

# 表头加列
hdr = t.rows[0]
last = hdr.cells[-1]
new_cell = copy.deepcopy(last._tc)
last._tc.addnext(new_cell)
hdr.cells[-1].text = ""
par = hdr.cells[-1].paragraphs[0]
par.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = par.add_run("实现状态")
if last.paragraphs[0].runs:
    src_run = last.paragraphs[0].runs[0]
    run.font.size = src_run.font.size
    run.font.bold = True
    run.font.name = src_run.font.name

for ri in range(1, len(t.rows)):
    row = t.rows[ri]
    fr = row.cells[0].text.strip()
    cell_src = row.cells[-1]
    new_tc = copy.deepcopy(cell_src._tc)
    cell_src._tc.addnext(new_tc)
    cell = row.cells[-1]
    cell.text = ""
    p_ = cell.paragraphs[0]
    p_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    status = STATUS.get(fr, "")
    extra = NOTE.get(fr, "")
    r_ = p_.add_run(status)
    if cell_src.paragraphs and cell_src.paragraphs[0].runs:
        sr = cell_src.paragraphs[0].runs[0]
        r_.font.size = sr.font.size
        r_.font.name = sr.font.name
        r_.font.bold = True
    if extra:
        r2 = p_.add_run("\n" + extra)
        if cell_src.paragraphs and cell_src.paragraphs[0].runs:
            r2.font.size = Pt(8)
            r2.font.name = "宋体"
            from docx.shared import RGBColor
            r2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

WIDTHS = [1.3, 2.8, 4.6, 1.3, 1.9, 2.7]
tblPr = t._tbl.tblPr
for el in tblPr.findall(qn("w:tblW")):
    tblPr.remove(el)
tw = OxmlElement("w:tblW")
tw.set(qn("w:w"), str(int(sum(WIDTHS) * 567)))
tw.set(qn("w:type"), "dxa")
tblPr.append(tw)
for row in t.rows:
    for i, w in enumerate(WIDTHS):
        row.cells[i].width = Cm(w)
print("表 3 已由 5 列扩展为 6 列（含实现状态）")

# ------------------------------------------------------------ 3. 附录 A
NORMAL = doc.styles["Normal"]


def para(text, size=12, bold=False, indent=True, align="justify", space_before=0):
    p_ = doc.add_paragraph()
    pf = p_.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.25
    pf.first_line_indent = Pt(size * 2) if indent else Pt(0)
    p_.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    r = p_.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().append(_east("宋体") if not bold else _east("黑体"))
    return p_


def _east(name):
    el = OxmlElement("w:rFonts")
    el.set(qn("w:ascii"), "Times New Roman")
    el.set(qn("w:hAnsi"), "Times New Roman")
    el.set(qn("w:eastAsia"), name)
    return el


def heading(text, size=16):
    p_ = doc.add_paragraph()
    pf = p_.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    pf.first_line_indent = Pt(0)
    r = p_.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().append(_east("黑体"))
    return p_


def cap(text):
    p_ = doc.add_paragraph()
    p_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p_.paragraph_format
    pf.space_before = Pt(3)
    pf.space_after = Pt(6)
    pf.first_line_indent = Pt(0)
    r = p_.add_run(text)
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().append(_east("黑体"))


def table(cap_text, headers, rows, widths):
    cap(cap_text)
    tt = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tt.alignment = WD_TABLE_ALIGNMENT.CENTER
    tt.autofit = False
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tt._tbl.tblPr.append(borders)
    for j, hd in enumerate(headers):
        c = tt.rows[0].cells[j]
        p_ = c.paragraphs[0]
        p_.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p_.add_run(hd)
        r.font.size = Pt(10.5)
        r.font.bold = True
        r.font.name = "Times New Roman"
        r._element.get_or_add_rPr().append(_east("宋体"))
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "E8EDF3")
        c._tc.get_or_add_tcPr().append(shd)
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = tt.rows[i].cells[j]
            p_ = c.paragraphs[0]
            pf = p_.paragraph_format
            pf.space_before = Pt(1)
            pf.space_after = Pt(1)
            pf.line_spacing = 1.0
            r = p_.add_run(str(val))
            r.font.size = Pt(10)
            r.font.name = "Times New Roman"
            r._element.get_or_add_rPr().append(_east("宋体"))
    for row in tt.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)


doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
heading("附录 A  一期（已实现）补充说明")

para("A.1 补充动机", bold=False)
para("正文第 2—4 章按项目整体规划编写，其中工单域（FR-07/08/09）属二期。为使需求文档与当前代码一致、便于验收对照，本附录补入一期实际交付的 2 层数据流图与两个核心用例，"
     "其内容与仓库 devSage 的实现（19 个接口、7 个工具、Chroma 向量库）一一对应。")

para("A.2 一期 2 层数据流图", bold=False)
pimg = doc.add_paragraph()
pimg.alignment = WD_ALIGN_PARAGRAPH.CENTER
pimg.add_run().add_picture(r"D:\课设\图片\dfd2.png", width=Cm(14.4))
cap("图 A-1  2 层数据流图（一期：文档入库与检索）")
para("图中 4.1 上传与解析、4.2 切分与去重、4.3 向量化与入库构成入库链路（异步，接口返回 202 后由任务轮询进度）；"
     "4.4 检索、重排与生成构成问答链路（SSE 流式，答案逐句标注来源）。数据存储 D5 记录文档元数据，D6 为 Chroma 向量库。")

para("A.3 一期核心用例", bold=False)
table("表 A-1  UC-A1 知识检索与问答（已实现）",
      ["项目", "内容"],
      [["用例编号", "UC-A1"],
       ["参与者", "研发人员（已登录）"],
       ["前置条件", "知识库已入库至少 1 篇文档；用户持有有效 JWT"],
       ["触发事件", "用户在工作台输入问题并提交"],
       ["基本路径", "① 前端 POST /api/chat/stream；② 意图路由判定为知识类；③ HyDE 扩展 → BM25 + 向量双路召回 → RRF 融合 → 重排取 Top-5；"
               "④ 组装提示词（片段带【来源】标记）→ 大模型流式生成；⑤ SSE 逐 token 推送，句末输出引用列表"],
       ["扩展路径", "E1 召回最高分 < 0.1 → 转联网搜索并在答案中标注网页来源；E2 模型超时 → 降级返回知识片段；E3 超出限流 → 返回 429"],
       ["后置条件", "本轮问答写入会话历史；相同问题命中缓存时直接返回"],
       ["验收标准", "首字延迟 ≤ 3 s；答案含至少 1 条可定位的引用；SSE 事件序列完整"]],
      [2.6, 12.0])
table("表 A-2  UC-A2 文档上传与入库（已实现）",
      ["项目", "内容"],
      [["用例编号", "UC-A2"],
       ["参与者", "研发人员（已登录）"],
       ["前置条件", "文件为 PDF/DOCX/Markdown/TXT 之一，大小 ≤ 50 MB"],
       ["触发事件", "用户选择文件上传"],
       ["基本路径", "① POST /api/document/upload；② 计算 MD5 去重；③ 投递 RabbitMQ 异步任务，接口立即返回 202 与 task_id；"
               "④ 后台解析 → 切分 → 向量化 → 写入 Chroma 与文档元数据；⑤ 前端轮询 /api/document/upload/status/{task_id} 直至完成"],
       ["扩展路径", "E1 文档重复（MD5 相同）→ 直接返回已存在文档；E2 解析失败 → 任务状态置失败并返回原因；E3 队列不可用 → 同步降级处理"],
       ["后置条件", "文档统计数 +1，切片统计 +N，BM25 索引重建，可被后续问答召回"],
       ["验收标准", "10 MB 文档端到端 ≤ 60 s；重复上传不产生重复文档"]],
      [2.6, 12.0])

para("A.4 与正文的对应关系", bold=False)
table("表 A-3  正文需求与一期实现对照",
      ["正文条目", "一期对应内容", "状态"],
      [["FR-03 知识文档上传", "UC-A2、图 A-1 的 4.1—4.3", "已实现"],
       ["FR-05 智能问答、FR-06 意图路由检索", "UC-A1、图 A-1 的 4.4", "已实现"],
       ["FR-11 高风险操作审批", "send_email 工具 interrupt + 前端审批卡片 + /api/chat/resume", "已实现"],
       ["FR-13 报告与交付", "报告生成（md→docx）、格式转换、邮件发送三工具", "已实现"],
       ["FR-16 多轮会话", "LangGraph checkpointer，thread_id 按用户+会话隔离", "已实现"],
       ["FR-02/12/14/15", "部分实现，详见正文表 3 备注", "部分实现"],
       ["FR-07/08/09 工单域", "二期规划，2 层分解见图 4", "二期"]],
      [4.8, 8.4, 2.2])

# 让 Word 打开时刷新目录页码
settings = doc.settings.element
if settings.find(qn("w:updateFields")) is None:
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)

doc.save(SRC)
print("saved:", SRC)
