# -*- coding: utf-8 -*-
"""系统概要设计说明书（一期：知识库 + 智能交付 Agent）"""
import copy
import json
import os
import sys

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, r"D:\课设\_lib")
import dlib

BASE = r"D:\课设"
TPL = os.path.join(BASE, "_tpl", "系统概要设计说明书模板202611.docx")
OUT = os.path.join(BASE, "智维台", "智维台_系统概要设计说明书.docx")
PAGES = os.path.join(BASE, "_lib", "toc_bd2.json")
IMG = os.path.join(BASE, "图片")
SHOT = os.path.join(BASE, "截图")
PROBE = os.environ.get("PROBE") == "1"

doc = Document(TPL)


def style_by_id(sid):
    for s in doc.styles:
        if s.style_id == sid:
            return s


ST_H1, ST_H2 = style_by_id("Heading1"), style_by_id("Heading2")


def set_font(run, size=12, east="宋体", ascii_f="Times New Roman", bold=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = ascii_f
    if color:
        from docx.shared import RGBColor
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), ascii_f)
    rFonts.set(qn("w:hAnsi"), ascii_f)
    rFonts.set(qn("w:eastAsia"), east)


def p(text, indent=True, size=12):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.25
    pf.first_line_indent = Pt(size * 2) if indent else Pt(0)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(par.add_run(text), size)
    return par


def code(text, size=9):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.0
    pf.first_line_indent = Pt(0)
    pf.left_indent = Pt(18)
    set_font(par.add_run(text), size, ascii_f="Consolas")


def h(level, text):
    par = doc.add_paragraph(style=ST_H1 if level == 1 else ST_H2)
    for r in par.runs:
        r.text = ""
    run = par.add_run(text)
    set_font(run, 22 if level == 1 else 16, east="黑体", ascii_f="Arial", bold=True,
             color=(0xC0, 0x00, 0x00) if PROBE else None)
    pf = par.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = True
    pPr = par._p.get_or_add_pPr()
    for ind in pPr.findall(qn("w:ind")):
        pPr.remove(ind)
    return par


counters = {"fig": 0, "tbl": 0}


def caption(text, kind):
    counters[kind] += 1
    label = ("图%d  " if kind == "fig" else "表%d  ") % counters[kind]
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(3)
    pf.space_after = Pt(6)
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = (kind == "tbl")
    set_font(par.add_run(label + text), 10.5, east="黑体")
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


def table(cap, headers, rows, widths, center=(), size=10.5, first_bold=False, mono_col=None):
    caption(cap, "tbl")
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


def figure(path, cap, width=14.2):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = par.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(0)
    par.add_run().add_picture(path, width=Cm(width))
    caption(cap, "fig")


# ------------------------------------------------------------------ 封面
for par in doc.paragraphs:
    if par.text.strip() == "系统":
        for r in par.runs:
            r.text = ""
        par.runs[0].text = "智维台（OpsDesk）"
        break
for par in doc.paragraphs:
    if par.text.strip().startswith("Version"):
        for r in par.runs:
            r.text = ""
        par.runs[0].text = "Version 1.0.0"
        break
for par in doc.paragraphs:
    if par.style is not None and par.style.name == "MonthYear":
        for r in par.runs[1:]:
            r.text = ""
        if par.runs:
            par.runs[0].text = "2026 年 11 月 20 日"
        break
for par in list(doc.paragraphs):
    if par.text.strip().startswith("注：在分工中"):
        par._p.getparent().remove(par._p)

_seen = False
for _ch in list(doc.element.body.iterchildren()):
    if _ch.tag == qn("w:tbl"):
        break
    if _ch.tag == qn("w:p"):
        _t = "".join(x.text or "" for x in _ch.iter(qn("w:t"))).strip()
        if _t.startswith("工学院"):
            _seen = True
            continue
        if _seen and not _t:
            doc.element.body.remove(_ch)

TEAM = [("冯嘉伟", "2420220019", "组长：总体架构、模块划分与接口设计", ""),
        ("杨文彬", "2420160092", "组员：检索链路、意图路由与评测", ""),
        ("刘文源", "2420160053", "组员：文档入库、数据模型与接口实现", ""),
        ("张琎", "2420160099", "组员：前端工作台、会话与审批卡片", ""),
        ("林景煌", "2410310023", "组员：部署视图、异步任务与文档整编", "")]
team_tbl = doc.tables[0]
while len(team_tbl.rows) < 1 + len(TEAM):
    team_tbl.add_row()
for i, row in enumerate(TEAM, start=1):
    for j, val in enumerate(row):
        cell = team_tbl.rows[i].cells[j]
        par = cell.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER if j in (0, 1, 3) else WD_ALIGN_PARAGRAPH.LEFT
        if par.runs:
            par.runs[0].text = val
            set_font(par.runs[0], 10.5)
        else:
            set_font(par.add_run(val), 10.5)

# ------------------------------------------------------------------ 目录
toc_title = None
for par in doc.paragraphs:
    if par.text.strip().replace(" ", "").replace("\u3000", "") == "目录":
        toc_title = par
        break
bio = doc.element.body
toc_paras, started = [], False
for child in list(bio.iterchildren()):
    if child is toc_title._p:
        started = True
        continue
    if not started:
        continue
    if child.tag == qn("w:p"):
        pPr = child.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
            break
        toc_paras.append(child)
    elif child.tag == qn("w:sdt"):
        bio.remove(child)
for el in toc_paras:
    for r in el.findall(qn("w:r")):
        el.remove(r)
for el in toc_paras[1:]:
    bio.remove(el)

toc_p = doc.paragraphs[0]
for par in doc.paragraphs:
    if par._p is (toc_paras[0] if toc_paras else None):
        toc_p = par
toc_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
run = toc_p.add_run()
fc = OxmlElement("w:fldChar")
fc.set(qn("w:fldCharType"), "begin")
fc.set(qn("w:dirty"), "true")
run._r.append(fc)
r2 = toc_p.add_run()
it = OxmlElement("w:instrText")
it.set(qn("xml:space"), "preserve")
it.text = ' TOC \\o "1-2" \\h \\z \\u '
r2._r.append(it)
r3 = toc_p.add_run()
sp = OxmlElement("w:fldChar")
sp.set(qn("w:fldCharType"), "separate")
r3._r.append(sp)


def toc_entry(text, page, level):
    par = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    st = OxmlElement("w:pStyle")
    st.set(qn("w:val"), "TOC%d" % level)
    pPr.append(st)
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:leader"), "dot")
    tab.set(qn("w:pos"), "8290")
    tabs.append(tab)
    pPr.append(tabs)
    sp_ = OxmlElement("w:spacing")
    sp_.set(qn("w:before"), "0")
    sp_.set(qn("w:after"), "0")
    sp_.set(qn("w:line"), "330")
    sp_.set(qn("w:lineRule"), "exact")
    pPr.append(sp_)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), {"1": "0", "2": "420"}[str(level)])
    ind.set(qn("w:firstLine"), "0")
    pPr.append(ind)
    par.append(pPr)
    rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:ascii"), "Times New Roman")
    rf.set(qn("w:hAnsi"), "Times New Roman")
    rf.set(qn("w:eastAsia"), "宋体")
    rPr.append(rf)
    b = OxmlElement("w:b")
    b.set(qn("w:val"), "1" if level == 1 else "0")
    rPr.append(b)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "22")
    rPr.append(sz)

    def mk(el):
        r = OxmlElement("w:r")
        r.append(copy.deepcopy(rPr))
        r.append(el)
        return r

    t_ = OxmlElement("w:t")
    t_.set(qn("xml:space"), "preserve")
    t_.text = text
    par.append(mk(t_))
    par.append(mk(OxmlElement("w:tab")))
    t2 = OxmlElement("w:t")
    t2.text = str(page)
    par.append(mk(t2))
    return par


anchor = toc_p._p
if (not PROBE) and os.path.exists(PAGES):
    with open(PAGES, encoding="utf-8") as f:
        entries = json.load(f)
    for item in entries:
        el = toc_entry(item["text"], item["page"], item["level"])
        anchor.addnext(el)
        anchor = el
    print("TOC entries:", len(entries))

end_r = OxmlElement("w:r")
efc = OxmlElement("w:fldChar")
efc.set(qn("w:fldCharType"), "end")
end_r.append(efc)
anchor.append(end_r)

settings = doc.settings.element
uf = OxmlElement("w:updateFields")
uf.set(qn("w:val"), "true")
settings.append(uf)

# ------------------------------------------------------------------ 删模板正文
body = doc.element.body
children = list(body.iterchildren())
start = None
for idx, ch in enumerate(children):
    if ch.tag == qn("w:p"):
        txt = "".join(t.text or "" for t in ch.iter(qn("w:t"))).strip()
        if txt == "修订历史":
            start = idx
            break
for ch in children[start:]:
    if ch.tag == qn("w:sectPr"):
        continue
    body.remove(ch)

# ================================================================== 正文
h(1, "1  修订历史")
table("修订历史", ["日期", "版本", "描述", "作者"],
      [["2026-11-16", "0.1", "初稿：架构分层、模块划分与部署视图", "冯嘉伟"],
       ["2026-11-19", "0.8", "补充数据视图与界面章节，与数据模型书对齐", "刘文源、张琎"],
       ["2026-11-20", "1.0", "评审定稿；明确一期范围与二期规划", "全组"]],
      [3.0, 2.0, 6.8, 2.8], center=(0, 1))

h(1, "2  概述")
h(2, "2.1  目的")
p("本文档给出智维台（OpsDesk）一期的概要设计：在《软件需求规格说明书》确定的需求基线之上，说明系统的总体结构、模块划分、数据组织与部署形态，作为详细设计、编码实现与验收测试的直接依据。")
p("读者对象包括：开发人员（据此划分包与接口）、测试人员（据此设计集成用例）、指导教师与评审人（据此判断设计是否覆盖需求、是否可实施）。方法级实现细节见配套的《系统详细设计说明书》。")
h(2, "2.2  范围")
p("本文档覆盖一期交付的五个能力域：认证与用户隔离、文档与知识库、检索问答、交付工具（报告生成/格式转换/邮件发送）、会话与记忆；并含审批与安全控制。工单建单、自动分派、SLA 与运营看板列为二期规划，不在本文档设计范围内。")
p("不涉及的内容：大模型训练与微调（仅调用推理接口）、企业现有 ITSM 系统的内部改造、硬件采购与机房建设。")

h(2, "2.3  定义及缩写")
table("定义及缩写", ["缩写", "定义"],
      [["RAG", "检索增强生成：先检索知识片段，再由大模型基于片段作答"],
       ["HyDE", "假设文档嵌入：先让模型生成假设答案，再用于向量召回"],
       ["BM25", "基于词频与逆文档频率的稀疏检索算法"],
       ["Rerank", "重排：用交叉编码模型对候选片段重新打分"],
       ["SSE", "Server-Sent Events，服务端单向流式推送"],
       ["LangGraph", "基于状态图的智能体编排框架，支持检查点与中断"],
       ["Checkpointer", "检查点持久化，保存会话记忆与执行状态"],
       ["HITL", "Human-in-the-Loop，人在回路：敏感动作需人工确认"],
       ["RBAC", "基于角色的访问控制（二期实现）"]],
      [2.6, 11.8], center=(0,), first_bold=True)

h(2, "2.4  参考")
table("参考资料", ["文档名称", "说明"],
      [["软件需求规格说明书（智维台）V1.1", "本项目组，含一期实现状态标注"],
       ["数据模型书（智维台）V1.0", "本项目组，实体与存储结构"],
       ["系统测试计划（智维台）V1.0", "本项目组，测试范围与用例"],
       ["FastAPI / Vue 3 官方文档", "接口与前端框架依据"],
       ["LangGraph 官方文档", "状态图、检查点与中断恢复"]],
      [6.4, 8.0], first_bold=True)

h(1, "3  项目背景")
h(2, "3.1  目标概要")
p("研发团队的技术规范、方案设计与复盘文档散落在网盘、群文件和 Wiki 中：新人上手靠问人，老人重复踩坑，写得再好也“找不到、用不上、留不住”。一期目标是让工程师用自然语言在散落文档里秒级找到答案，并完成“检索 → 交付”的闭环——答案可追溯、报告可直接产出、邮件发送有审批。")
p("量化目标：知识类问题检索覆盖率 100%，答案必带可定位引用；首字延迟 ≤ 3 s；Agent 端到端评测 38/38 通过；相同问题缓存命中后延迟 ≤ 0.1 s。")

h(2, "3.2  方案概要")
p("技术路线为“三阶混合检索 + 状态图智能体”：检索侧 HyDE 语义扩展 → BM25 关键词召回 → 交叉编码重排，召回不足时自动转联网搜索兜底；生成侧由 LangGraph 状态图编排，把“先检索知识库”从提示词约束升级为图上的必经节点，再进入 ReAct 工具循环。")
p("架构风格为分层单体：五个包（api / services / domain / adapters / common）单向依赖，部署为一台主机上的 Docker Compose；智能体的会话记忆与执行状态由 SQLite 检查点持久化，刷新、切会话、换设备均可恢复。")
p("交付能力通过 7 个函数调用工具实现：检索、上传、删除、统计、报告生成、格式转换、邮件发送；其中邮件发送属敏感动作，执行前 interrupt 挂起，前端弹出审批卡片，确认后 resume 继续。")

h(1, "4  硬件及软件")
p("系统为 B/S 结构，服务端以 Docker Compose 编排在一台内网主机上运行；开发与联调可在单机直接启动。软硬件配置如表 4 所示。")
table("软硬件环境", ["类别", "配置项", "规格说明"],
      [["服务器", "CPU / 内存 / 磁盘", "8 核 16 GB / 200 GB SSD（向量库与上传文件占用为主）"],
       ["服务器", "操作系统", "Ubuntu Server 22.04 LTS"],
       ["服务器", "运行时", "Docker Engine 24 + Docker Compose v2"],
       ["开发机", "操作系统", "Windows 11 / macOS 14"],
       ["开发机", "运行时", "Python 3.11（含 .venv）、Node.js 20"],
       ["客户端", "浏览器", "Chrome / Edge 100 以上，支持 SSE"],
       ["网络", "带宽与出口", "内网千兆；需可访问模型 API（或配置内网代理）"],
       ["外部依赖", "模型服务", "兼容 OpenAI Chat Completions 协议的 LLM 与 Embedding 接口"]],
      [2.4, 3.8, 8.4], center=(0,), first_bold=True)

h(1, "5  外部因素")
h(2, "5.1  存在的应用软件")
p("企业已有 OA、邮件系统与即时通讯工具。一期不替换这些系统，仅通过 SMTP 发送交付邮件；用户认证为系统内自建（JWT），后续可接入企业统一身份认证。")

h(2, "5.2  第三方应用软件")
p("系统依赖的第三方服务与库如表 5 所示。模型调用统一收敛在网关模块，供应商可切换，业务代码不感知具体厂商。")
table("第三方软件与服务", ["名称", "用途", "接入方式", "备注"],
      [["DeepSeek / 智谱 GLM", "问答生成、要素抽取、意图分类", "HTTPS，OpenAI 兼容协议", "可切换，超时降级"],
       ["Embedding 模型", "文档切片与查询向量化", "HTTPS 或本地推理", "维度随模型而定"],
       ["BGE-Reranker", "候选片段重排", "本地推理 / API", "阈值 0.1 过滤低质"],
       ["Chroma", "向量库，持久化切片向量", "进程内 PersistentClient", "集合 knowledge_chunks"],
       ["Redis", "热点缓存与上传临时文件", "RESP", "未启动则缓存降级"],
       ["RabbitMQ", "文档异步解析队列", "AMQP", "未启动则同步降级"],
       ["博查 web_search", "本地检索不足时联网兜底", "HTTPS", "标注网页来源与日期"]],
      [4.0, 4.6, 4.4, 2.2], first_bold=True)

h(2, "5.3  外部数据源")
p("一期数据源为研发团队自有文档：技术规范、方案设计、复盘与会议纪要，格式为 PDF、DOCX、Markdown、TXT。文档经上传接口入库，原文保存在 app/data/uploads，切片向量写入 Chroma，元数据与摘要用于统计与引用回填。")

h(1, "6  技术技能")
p("团队采用的技术栈与掌握程度如表 6 所示。选型原则是“团队已掌握或一周内可掌握”，并且优先选择可私有化部署的开源组件。")
table("技术栈", ["层次", "选型", "用途", "掌握程度"],
      [["前端", "Vue 3 + Vite + 原生 composables", "工作台、会话侧栏、审批卡片", "熟练"],
       ["前端", "SSE（EventSource / fetch stream）", "流式渲染与打字机效果", "熟练"],
       ["后端", "Python 3.11 + FastAPI + Pydantic v2", "REST/SSE 接口与参数校验", "熟练"],
       ["编排", "LangGraph（StateGraph + Checkpointer）", "智能体状态图、记忆与中断", "一般"],
       ["检索", "BM25 + Chroma + BGE-Reranker + HyDE", "三阶混合检索", "一般"],
       ["工程", "Docker / pytest / Ruff / GitHub Actions", "部署、测试与持续集成", "熟练"]],
      [2.0, 6.0, 5.2, 1.4], center=(0, 3), first_bold=True)

h(1, "7  解决方案架构")
h(2, "7.1  系统体系结构")
p("系统采用五层体系结构：表现层（Vue 3 工作台）、接口层（FastAPI 路由与 SSE）、应用服务层（认证、文档、检索、交付、会话五个服务）、能力层（三阶检索、意图路由、LangGraph 状态图、工具调用、人工审批）、基础设施层（SQLite、Chroma、Redis、RabbitMQ、模型 API）。层间只向下依赖，如图 1 所示。")
figure(os.path.join(IMG, "arch.png"), "系统总体架构", 14.6)
p("三个关键设计决策：其一，问答链路走 SSE 而非轮询，保证首字延迟与打字机体验；其二，把“先检索”做成状态图的必经节点而不是提示词要求，知识类问题检索覆盖率因此达到 100%；其三，会话记忆与审批状态落在检查点，而不是进程内存，使中断可恢复、换设备可续。")
p("分层约束：api 层只做参数校验与响应组装；services 层编排用例，不直接访问数据库细节；domain 层放实体与规则；adapters 实现仓储与外部调用；common 提供配置、日志与错误处理。该约束由代码评审与 CI 静态检查保证。")

h(2, "7.2  网络和通讯视图")
p("部署视图如图 2 所示：浏览器经内网访问 api 容器的 9000 端口（FastAPI 同时托管 Vue 构建产物），api 通过 Redis 做缓存与临时文件、通过 RabbitMQ 投递异步解析任务、通过数据卷持久化 SQLite 与 Chroma；外部仅三个出口——模型 API、SMTP 邮箱、博查搜索。")
figure(os.path.join(IMG, "deploy.png"), "部署与网络视图（Docker Compose）", 14.6)
p("通讯协议：前后端为 HTTPS + JSON；问答与工具调用为 SSE 单向流，事件类型包括 start、delta、tool、citation、approval、done、error；内部为进程内调用；异步任务通过 AMQP 投递，任务状态以 task_id 轮询。")

h(2, "7.3  模块视图")
p("系统按能力划分为六个模块（M1—M6），结构如图 3 所示。模块之间只经应用服务层接口调用，不共享数据表。")
figure(os.path.join(IMG, "module.png"), "系统模块结构（一期六模块）", 14.2)
table("模块清单", ["编号", "模块", "主要职责", "对外接口", "负责人"],
      [["M1", "认证与用户", "注册、登录、令牌校验、资料与改密", "/api/auth/*", "冯嘉伟"],
       ["M2", "会话与记忆", "会话增删改查、多轮上下文、检查点持久化", "/api/chat/sessions 等", "张琎"],
       ["M3", "文档与知识库", "上传、解析、切片去重、向量入库、统计与删除", "/api/document/*", "刘文源"],
       ["M4", "检索问答", "意图路由、混合召回、重排、生成与引用", "/api/chat/stream", "杨文彬"],
       ["M5", "交付工具", "报告生成、格式转换、邮件发送、文件下载", "工具调用（内部）", "杨文彬"],
       ["M6", "审批与安全", "人工审批、中断恢复、限流防呆、操作留痕", "/api/chat/resume、/pending", "林景煌"]],
      [1.2, 2.8, 6.4, 3.4, 1.6], center=(0, 4), first_bold=True)
p("模块边界约定：M3 只负责文档与切片，不承担检索排序；M4 只读切片与元数据，不修改知识库；M5 的工具调用统一登记在工具注册表，新增工具不改动 M4 的路由逻辑；M6 的审批状态由检查点托管，任何模块不得绕过。")

h(2, "7.4  数据视图")
p("数据结构分三个存储域：关系型（SQLite 的 users 表）、会话域（按用户分文件的会话与消息）、知识域（文档元数据 + Chroma 切片向量），另有检查点库承载智能体状态。实体关系如图 4 所示。")
figure(os.path.join(IMG, "er.png"), "系统 ER 图（按存储介质着色）", 14.4)
table("数据集合概览", ["数据集合", "存储介质", "主键", "说明"],
      [["users", "SQLite（app.db）", "id", "账号与资料，唯一索引 username"],
       ["session / message", "文件（chat_history/<uid>）", "session_id / message_id", "会话标题、消息正文与引用"],
       ["document", "目录 + 元数据", "doc_id", "原件、类型、大小、切片数"],
       ["chunk", "Chroma 向量库", "chunk_id", "切片正文、元数据与向量"],
       ["checkpoint", "SQLite（checkpoints.db）", "thread_id + checkpoint_id", "智能体状态与中间写入"]],
      [3.4, 5.4, 3.4, 4.6], first_bold=True)
p("设计取舍：会话与消息以文件存储而非关系表，因为读写以“整段会话”为单位、无跨会话关联查询；切片向量交给向量库托管，主库只保留 chunk_count 统计。代价是统计需遍历文件，因此统计接口做了一层缓存。详细字段见《数据模型书》。")

h(2, "7.5  用户界面")
p("一期共四个主要界面：登录/注册、对话工作台（含会话侧栏与文档上传）、审批卡片（模态）、设置与个人资料。工作台界面如图 5 所示。")
figure(os.path.join(SHOT, "shot_chat_qa.png"), "对话工作台（问答、工具结果与引用来源）", 14.4)
p("界面设计三条原则：一是“一句话即可开始”，输入框常驻、不要求先选分类；二是“答案必带出处”，回答下方列出引用来源并可展开；三是“敏感动作必须显式确认”，发邮件前弹出审批卡片，未确认前输入区锁定。")

h(1, "8  未鉴别因素")
p("（1）真实数据规模未知：当前知识库仅 9 篇文档、39 条切片，规模放大到数百篇后检索延迟与召回质量需重新评估。（2）模型供应商稳定性：外部 API 的限流与超时会影响端到端体验，当前以缓存与降级应对，未做多供应商自动切换。（3）企业内网出网限制：若无法访问外部模型，需改为本地模型部署，架构需增加模型服务容器。")

h(1, "9  研发风险")
table("研发风险与应对", ["编号", "风险", "概率", "影响", "应对措施"],
      [["R1", "检索质量不达预期，答案不可用", "中", "高", "以 300 题检索评测集驱动调优；重排阈值 + 联网兜底"],
       ["R2", "智能体越权执行敏感动作", "低", "高", "工具白名单 + interrupt 人工审批 + 检查点回滚"],
       ["R3", "模型接口超时或限流", "中", "中", "超时重试、缓存命中、非生成类接口本地兜底"],
       ["R4", "异步链路（Redis/RabbitMQ）不可用", "中", "中", "降级为同步处理，接口返回 202 + 任务轮询"],
       ["R5", "进度延期导致功能裁剪", "中", "中", "按 P0/P1 排序，优先保证问答与上传闭环"],
       ["R6", "团队对 LangGraph 不熟", "中", "中", "第 1 周完成技术预研，先跑通最小状态图"]],
      [1.1, 5.6, 1.2, 1.2, 4.6], center=(0, 2, 3), first_bold=True)

# ------------------------------------------------------------------ 去除文档网格、填充页眉
for _s in doc.sections:
    _sp = _s._sectPr
    _dg = _sp.find(qn("w:docGrid"))
    if _dg is None:
        _dg = OxmlElement("w:docGrid")
        _sp.append(_dg)
    _dg.set(qn("w:type"), "none")
    _hdr = _s.header
    if _hdr is None:
        continue
    for _hp in _hdr.paragraphs:
        if any("项目名" in _r.text for _r in _hp.runs):
            from docx.enum.text import WD_TAB_ALIGNMENT as _TA
            _hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _hp.paragraph_format.tab_stops.add_tab_stop(Cm(7.2), _TA.CENTER)
            _hp.paragraph_format.tab_stops.add_tab_stop(Cm(14.2), _TA.RIGHT)
            _hp.runs[0].text = "项目名：智维台\t概要设计说明书\t组号：第 5 组"
            for _r in _hp.runs[1:]:
                _r.text = ""

# ------------------------------------------------------------------ 页码格式
try:
    _secs = doc.sections
    if len(_secs) >= 3:
        _toc_sp = _secs[1]._sectPr
        _pn = _toc_sp.find(qn("w:pgNumType"))
        if _pn is None:
            _pn = OxmlElement("w:pgNumType"); _toc_sp.append(_pn)
        _pn.set(qn("w:fmt"), "lowerRoman"); _pn.set(qn("w:start"), "1")
        _body_sp = _secs[2]._sectPr
        _pn3 = _body_sp.find(qn("w:pgNumType"))
        if _pn3 is None:
            _pn3 = OxmlElement("w:pgNumType"); _body_sp.append(_pn3)
        _pn3.set(qn("w:fmt"), "decimal"); _pn3.set(qn("w:start"), "1")
except Exception as _e:
    print("页码设置跳过:", _e)

# ------------------------------------------------------------------ 页脚页码
for i, sec in enumerate(doc.sections):
    if i == 0:
        ftr = sec.footer
        ftr.is_linked_to_previous = False
        el = ftr._element
        for ch in list(el):
            el.remove(ch)
        el.append(OxmlElement("w:p"))
        continue
    ftr = sec.footer
    ftr.is_linked_to_previous = False
    el = ftr._element
    for ch in list(el):
        el.remove(ch)
    newp = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    pPr.append(jc)
    newp.append(pPr)
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "21")
    rpr.append(sz)

    def run(child):
        r = OxmlElement("w:r")
        r.append(copy.deepcopy(rpr))
        r.append(child)
        return r

    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    newp.append(run(f1))
    it2 = OxmlElement("w:instrText")
    it2.set(qn("xml:space"), "preserve")
    it2.text = " PAGE "
    newp.append(run(it2))
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "separate")
    newp.append(run(f2))
    t3 = OxmlElement("w:t")
    t3.text = "1"
    newp.append(run(t3))
    f3 = OxmlElement("w:fldChar")
    f3.set(qn("w:fldCharType"), "end")
    newp.append(run(f3))
    el.append(newp)

name = "probe_bd2.docx" if PROBE else OUT
doc.save(name)
print("saved:", name, "tables", len(doc.tables))
