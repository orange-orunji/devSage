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
TPL = os.path.join(BASE, "_tpl", "系统详细设计说明书模板202611.docx")
OUT = os.path.join(BASE, "智维台", "智维台_系统详细设计说明书.docx")
PAGES = os.path.join(BASE, "_lib", "toc_dd.json")
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


PROBE_MAP = []


def h(level, text):
    par = doc.add_paragraph(style=ST_H1 if level == 1 else ST_H2)
    for r in par.runs:
        r.text = ""
    run = par.add_run(text)
    _color = None
    if PROBE:
        _i = len(PROBE_MAP)
        _color = (150 + (_i * 5) % 90, 10 + (_i * 11) % 60, 10 + (_i * 7) % 60)
        PROBE_MAP.append({"idx": _i, "text": text, "level": level, "color": list(_color)})
    set_font(run, 22 if level == 1 else 16, east="黑体", ascii_f="Arial", bold=True,
             color=_color)
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
for ch in children[start:]:
    if ch.tag == qn("w:sectPr"):
        continue
    body.remove(ch)

# 正文由 dd_content.py 提供
# -*- coding: utf-8 -*-
"""正文内容：详细设计说明书（被 build_dd.py 拼接使用）。"""

h(1, "1  修订历史")
table("修订历史", ["日期", "版本", "描述", "作者"],
      [["2026-11-17", "0.1", "初稿：包视图、抽象类视图", "冯嘉伟"],
       ["2026-11-19", "0.7", "补时序图、类/接口视图与数据库定义", "刘文源、杨文彬"],
       ["2026-11-20", "1.0", "补六模块处理流程与界面控件表，评审定稿", "全组"]],
      [3.0, 2.0, 7.2, 2.4], center=(0, 1))

h(1, "2  绪言和目标")
p("本文档是《系统概要设计说明书》的下层设计，把概设中的模块与接口细化到类、方法、数据表与处理流程一级，使编码有明确依据、测试有可核对的对象。")
p("目标有三：一是给出接口与类的签名约定，避免前后端各自命名；二是给出关键链路的时序与异常分支，明确超时、降级与中断恢复的处理位置；三是给出六个模块的处理流程与界面控件定义，使实现与需求条目一一对应。")
p("读者对象：开发人员（据此编码）、测试人员（据此设计接口与集成用例）、评审人（据此判断设计是否可实现、是否覆盖需求）。")

h(1, "3  范围")
p("覆盖一期已实现的六个模块：M1 认证与用户、M2 会话与记忆、M3 文档与知识库、M4 检索问答、M5 交付工具、M6 审批与安全；以及 19 个对外接口、7 个函数调用工具、users 表与文件/向量混合存储。")
p("不覆盖：二期工单域（建单、分派、状态机、SLA）、模型训练与微调、前端工程化构建细节（见 README 与 CI 配置）。")

h(1, "4  定义及缩写")
table("定义及缩写", ["术语/缩写", "说明"],
      [["SSE", "Server-Sent Events，服务端单向流式推送"],
       ["端口（Port）", "services 层定义的抽象接口，由 adapters 实现"],
       ["适配器（Adapter）", "对数据库、向量库、模型、邮件等外部依赖的实现类"],
       ["中断（Interrupt）", "LangGraph 在执行前挂起，等待外部输入后恢复"],
       ["检查点（Checkpoint）", "智能体状态快照，含消息与工具调用中间结果"],
       ["RRF", "倒数排名融合，把 BM25 与向量两路结果合并"],
       ["幂等（Idempotent）", "同一请求重复执行不产生重复数据"]],
      [3.4, 11.0], center=(0,), first_bold=True)

h(1, "5  引用")
table("引用文件", ["文档名称", "版本/来源", "用途"],
      [["系统概要设计说明书（智维台）", "V1.0", "模块与接口的上层约束"],
       ["数据模型书（智维台）", "V1.0", "实体、字段与存储结构"],
       ["软件需求规格说明书（智维台）", "V1.1", "需求编号与验收标准"],
       ["FastAPI / Pydantic v2 文档", "官方", "路由、依赖注入与校验"],
       ["LangGraph 文档", "官方", "StateGraph、checkpointer 与 interrupt"]],
      [6.4, 4.0, 4.2], first_bold=True)

h(1, "6  角色及职责")
table("角色与职责", ["角色", "职责", "对应成员"],
      [["架构与接口", "分层约束、接口签名、评审", "冯嘉伟"],
       ["检索与生成", "路由、召回、重排、提示词与评测", "杨文彬"],
       ["文档与数据", "上传解析、切片、向量入库、数据校验", "刘文源"],
       ["前端与交互", "工作台、会话、审批卡片与流式渲染", "张琎"],
       ["部署与质量", "容器编排、异步任务、测试与文档", "林景煌"]],
      [3.2, 8.6, 3.0], center=(0,), first_bold=True)

h(1, "7  工具及环境")
h(2, "7.1  研发硬件配置")
table("研发硬件配置", ["用途", "配置", "说明"],
      [["开发机", "16 GB 内存 / 512 GB SSD / Windows 11", "本地起服务与调试"],
       ["测试/演示机", "8 核 16 GB / Ubuntu 22.04", "Docker Compose 部署"],
       ["模型调用", "公网或代理出口", "LLM 与 Embedding 接口"]],
      [3.0, 7.4, 4.4], center=(0,))

h(2, "7.2  研发语言及编译器")
table("语言与运行时", ["语言/框架", "版本", "用途"],
      [["Python", "3.11", "后端与脚本，虚拟环境 .venv"],
       ["TypeScript / JavaScript", "ES2022", "前端，Node 20 构建"],
       ["SQL", "SQLite 3", "users 表与检查点库"],
       ["Dockerfile / YAML", "Compose v2", "镜像构建与编排"]],
      [5.0, 3.6, 6.0], center=(1,))

h(2, "7.3  软件支持工具")
table("软件支持工具", ["工具", "用途"],
      [["pytest", "单元与接口测试，CI 中执行 P0 冒烟用例"],
       ["Ruff", "静态检查与格式统一"],
       ["Vite", "前端构建与开发热更新"],
       ["GitHub Actions", "双 job CI（后端测试 + 前端构建）"],
       ["Chroma / SQLite Browser", "向量库与本地库检视"]],
      [4.6, 10.0], first_bold=True)

h(2, "7.4  第三方工具")
table("第三方依赖", ["组件", "版本/形态", "作用"],
      [["langgraph", "进程内库", "状态图编排、检查点与中断"],
       ["chromadb", "本地持久化", "切片向量存储与相似检索"],
       ["redis", "容器/本机", "热点缓存、上传临时文件"],
       ["rabbitmq", "容器/本机", "文档异步解析队列"],
       ["openai-sdk 兼容客户端", "HTTPS", "LLM 与 Embedding 调用"],
       ["jieba / rank-bm25", "进程内库", "中文分词与 BM25 索引"]],
      [4.6, 4.2, 5.8], first_bold=True)

h(1, "8  高层分析")
h(2, "8.1  数据模型视图")
p("数据分三个存储域：关系型（users）、会话域（按用户分文件的会话与消息）、知识域（文档元数据 + Chroma 切片），另有检查点库。实体关系见图 1，字段定义见《数据模型书》第 2 章。")
figure(os.path.join(IMG, "er.png"), "系统 ER 图（按存储介质着色）", 14.4)
p("选择文件存储会话而非关系表，是因为消息体含长 Markdown 与引用数组、读写以整段会话为单位；选择 Chroma 托管切片，是因为向量检索需要 HNSW 索引，关系库无法高效支持。")

h(2, "8.2  抽象类视图")
p("系统以端口—适配器方式组织：services 层定义五个接口（AuthService、DocService、RagService、ToolRegistry、StateGraph），adapters 提供 SQLite 仓储、Chroma 向量库、模型网关、邮件发送与队列实现；domain 层只放实体与自身校验。接口与实体的关系见图 2。")
figure(os.path.join(IMG, "dd_abstract.png"), "抽象类视图（接口与领域实体）", 14.6)
table("接口与主要实现", ["接口", "实现类", "职责边界"],
      [["AuthService", "auth_service.AuthService", "注册登录、令牌签发与校验、改密"],
       ["DocService", "doc_service.DocService", "上传、解析、切片、入库、统计、下架"],
       ["RagService", "rag_service.RagService", "意图路由、混合召回、重排、生成"],
       ["ToolRegistry", "services.tools.*", "工具注册与分发、敏感动作拦截"],
       ["StateGraph", "agent.agent.build_graph", "图编排、检索必经节点、中断恢复"]],
      [3.2, 5.6, 6.0], first_bold=True)

h(2, "8.3  时序图")
p("问答链路是系统最关键、分支最多的路径。图 3 给出从浏览器发起到流式返回的完整时序，含检索不足转联网、工具调用、审批中断与检查点落盘四个扩展点。")
figure(os.path.join(IMG, "dd_seq.png"), "问答链路时序图", 15.0)
table("时序消息说明", ["序号", "消息", "说明", "异常处理"],
      [["1", "POST /chat/stream", "携带问题与会话 ID，Bearer 令牌校验", "401 / 422 / 429"],
       ["3", "route(question)", "三层漏斗：正则 → IDF 稀有词 → 语义分类", "分类失败默认按知识类"],
       ["4-6", "retrieve / rerank", "HyDE 扩展 → BM25 + 向量 → RRF → 重排", "召回分 < 0.1 转联网搜索"],
       ["8-9", "generate / token 流", "提示词注入片段并按 token 推送", "超时重试一次，仍失败返回降级答案"],
       ["10", "tool call", "工具调用与结果回填", "工具异常封装为结构化错误"],
       ["13", "save_checkpoint", "状态写入 checkpoints.db", "写失败不影响本次响应"]],
      [1.4, 4.4, 6.4, 4.4], center=(0,), first_bold=True)

h(2, "8.4  用户界面架构")
p("前端为单页应用，无路由库，用组合式状态驱动视图切换：App 根据令牌决定渲染登录页或工作台；工作台由侧栏（会话列表、上传入口）与主区（消息流、输入框、审批卡片）组成，状态集中在三个 composable 中。")
table("界面组件与状态", ["组件", "职责", "依赖状态"],
      [["App.vue", "登录态判定与视图切换", "useAuth.token"],
       ["LoginView.vue", "登录/注册表单与错误提示", "useAuth"],
       ["ChatView / ChatArea", "消息流渲染、SSE 接收、工具提示", "useMessages"],
       ["Sidebar", "会话列表、搜索、置顶、新建与删除", "useSessions"],
       ["ApprovalCard", "审批卡片：确认/驳回、输入锁定", "useMessages.pending"]],
      [3.8, 7.6, 4.0], first_bold=True)

h(1, "9  详细分析")
h(2, "9.1  类/接口视图")
p("核心实现类与其公开方法见图 4。图中蓝色为接口层、绿色为知识能力、橙色为编排能力、灰色为适配器；箭头标注组合与调用关系。")
figure(os.path.join(IMG, "dd_class.png"), "类/接口视图（核心实现类）", 15.0)
table("关键方法签名", ["类", "方法", "入参 / 出参", "说明"],
      [["ChatRouter", "stream_chat", "body: ChatRequest → StreamingResponse", "限流 10/min，转 SSE"],
       ["RagService", "ask", "q, sid → AsyncIterator[str]", "编排检索与生成，逐 token 产出"],
       ["RagService", "retrieve", "q → list[Chunk]", "混合召回 + 重排，带来源元数据"],
       ["DocService", "upload", "file, uid → task_id", "落盘 + MD5 去重 + 投递队列"],
       ["DocService", "handle_task", "task_id → None", "解析、切片、向量化、写库"],
       ["SessionService", "history", "sid → list[Message]", "读会话文件，按时间排序"],
       ["ToolRegistry", "dispatch", "name, kwargs → Any", "校验白名单后执行工具"],
       ["ToolRegistry", "interrupt_if_sensitive", "name → bool", "发邮件等动作挂起等待审批"]],
      [3.4, 4.2, 5.6, 4.6], first_bold=True)

h(2, "9.2  构件/包视图")
p("代码按五个包组织，依赖方向单向：api → services → domain；adapters 实现 services 定义的端口；common 被各层引用。禁止反向 import，由评审与静态检查保证。")
figure(os.path.join(IMG, "dd_pkg.png"), "构件/包视图", 14.4)
table("包与依赖规则", ["包", "允许依赖", "禁止依赖", "典型内容"],
      [["api", "services, common", "adapters 实现细节", "路由、鉴权依赖、SSE 编码"],
       ["services", "domain, common, 端口", "api", "用例编排、事务边界"],
       ["domain", "common", "services, adapters", "实体、值对象、规则"],
       ["adapters", "domain, common", "api", "仓储、向量库、模型网关、邮件"],
       ["common", "无", "以上任意", "配置、日志、错误、重试"]],
      [2.4, 4.0, 3.6, 5.2], first_bold=True)

h(1, "10  详细设计")
h(2, "10.1  数据库定义")
p("关系库只有 users 一张表，其余数据以文件与向量库形式存放。建表语句与运行环境一致（含唯一索引），会话文件为按用户分文件的 JSON 结构。")
code("""CREATE TABLE users (
    id INTEGER NOT NULL,
    username VARCHAR,
    hashed_password VARCHAR,
    display_name VARCHAR DEFAULT '',
    avatar VARCHAR DEFAULT '',
    bio VARCHAR DEFAULT '',
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);""")
table("users 字段定义", ["字段", "类型", "约束", "说明"],
      [["id", "INTEGER", "PK 自增", "用户主键"],
       ["username", "VARCHAR", "唯一索引", "登录名，注册时校验长度与重复"],
       ["hashed_password", "VARCHAR", "非空", "bcrypt 哈希，不可逆"],
       ["display_name", "VARCHAR", "默认空串", "界面问候用语"],
       ["avatar", "VARCHAR", "默认空串", "头像相对路径"],
       ["bio", "VARCHAR", "默认空串", "个人简介"]],
      [3.4, 3.0, 3.4, 5.6], center=(0,), first_bold=True)
p("会话文件结构（app/data/chat_history/<user_id>）为 {\"sessions\": [{session_id, title, created_at, updated_at, messages: [{message_id, role, content, citations, created_at}]}]}；"
  "切片存于 Chroma 集合 knowledge_chunks，元数据含 doc_id、seq、doc_name，用于引用回填。")

h(2, "10.2  用户界面设计")
p("工作台以“左栏会话、右区对话、底部输入”的经典三分布局实现，关键控件与校验规则如表 12，界面实景见图 5。")
figure(os.path.join(SHOT, "shot_chat_qa.png"), "对话工作台（工具结果与引用来源）", 14.4)
table("界面控件与校验", ["控件", "位置", "行为", "校验与异常"],
      [["用户名 / 密码", "登录页", "登录或注册", "空值禁用按钮；错误显示 401 提示"],
       ["输入框", "工作台底部", "Enter 发送，Shift+Enter 换行", "超长 422；空内容不发送"],
       ["发送按钮", "输入框右侧", "触发 /chat/stream", "流式期间禁用，防重复提交"],
       ["会话项", "左侧栏", "切换、重命名、删除", "删除需二次确认；搜索按标题模糊匹配"],
       ["上传入口", "侧栏底部", "选择文件上传并轮询状态", "格式白名单；>50 MB 拒绝"],
       ["审批卡片", "消息流内", "确认 / 驳回，锁定输入区", "无权限或超时提示失败原因"]],
      [3.6, 3.2, 5.0, 6.0], first_bold=True)

h(2, "10.3  六模块处理流程")
p("各模块的处理流程以其主用例为线索，逐步给出输入、处理与输出，异常分支单独列出，便于测试按步核对。")
table("M1 认证与用户", ["步骤", "处理", "输出/异常"],
      [["1", "接收用户名与密码，校验长度与字符集", "422 参数错误"],
       ["2", "查 users 表并 bcrypt 校验", "401 用户名或密码错误"],
       ["3", "签发 JWT（含 user_id，有效期可配）", "返回 access_token"],
       ["4", "后续请求经依赖项解析令牌", "401 令牌无效或过期"]],
      [1.2, 8.6, 5.0], center=(0,))
table("M2 会话与记忆", ["步骤", "处理", "输出/异常"],
      [["1", "按 user_id 读取会话文件，按更新时间排序", "空列表"],
       ["2", "新建会话生成 session_id 并写入空会话", "写失败回滚内存状态"],
       ["3", "重命名/删除同步更新文件与检查点", "会话不存在返回 404"],
       ["4", "问答时以 thread_id=用户+会话 读取历史", "历史超长按窗口裁剪"]],
      [1.2, 8.6, 5.0], center=(0,))
table("M3 文档与知识库", ["步骤", "处理", "输出/异常"],
      [["1", "接收上传，校验扩展名与大小，计算 MD5", "415 格式不支持 / 413 超限"],
       ["2", "MD5 已存在则直接返回已入库文档", "幂等，不重复入库"],
       ["3", "投递 RabbitMQ 异步任务，返回 task_id", "队列不可用降级为同步"],
       ["4", "后台解析 → 切分 → 向量化 → 写 Chroma", "解析失败置 failed 并记录原因"],
       ["5", "重建 BM25 索引并更新统计", "统计数与实际条目不一致时告警"]],
      [1.2, 8.6, 5.0], center=(0,))
table("M4 检索问答", ["步骤", "处理", "输出/异常"],
      [["1", "意图路由：正则命中 → IDF 稀有词 → 语义分类", "分类失败按知识类处理"],
       ["2", "HyDE 生成假设答案用于向量召回", "生成失败退化为原问题"],
       ["3", "BM25 与向量双路召回，RRF 融合后重排", "最高分 < 0.1 转联网搜索"],
       ["4", "片段注入提示词，要求句末标注来源", "模型超时重试一次"],
       ["5", "SSE 推送 delta 与 citation，结束发送 done", "客户端断开则中止生成"]],
      [1.2, 8.6, 5.0], center=(0,))
table("M5 交付工具", ["步骤", "处理", "输出/异常"],
      [["1", "模型返回 tool_calls，路由到 ToolRegistry", "未知工具返回错误事件"],
       ["2", "报告生成：汇总片段 → Markdown → docx", "转换失败返回原始 Markdown"],
       ["3", "邮件发送：拼装正文与附件，先检查审批", "未审批则中断，不发送"],
       ["4", "返回下载链接或发送结果", "SMTP 失败重试两次后报错"]],
      [1.2, 8.6, 5.0], center=(0,))
table("M6 审批与安全", ["步骤", "处理", "输出/异常"],
      [["1", "敏感工具执行前 interrupt，返回审批卡事件", "状态写入检查点"],
       ["2", "前端展示卡片并锁定输入区", "刷新/切会话后按 pending 重建"],
       ["3", "用户确认 → /chat/resume 恢复执行", "驳回则结束并记录结论"],
       ["4", "全程限流、鉴权与操作日志", "429 / 401 / 日志留痕"]],
      [1.2, 8.6, 5.0], center=(0,))
p("一致性要求：六个模块的异常码统一为 400/401/403/404/413/415/422/429/500 九类；所有对外错误体为 {\"detail\": \"...\"}，不返回堆栈；工具调用的中间结果只经 SSE 事件传递，不写入会话正文。")


# ------------------------------ 收尾（页码格式/页脚）

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

name = "probe_dd.docx" if PROBE else OUT
doc.save(name)
if PROBE:
    import json as _json
    _json.dump(PROBE_MAP, open(os.path.join(BASE, "_lib", "probe_map_dd.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)
    print("probe map:", len(PROBE_MAP))
print("saved:", name, "tables", len(doc.tables))
