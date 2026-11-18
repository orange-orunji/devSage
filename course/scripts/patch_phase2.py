# -*- coding: utf-8 -*-
"""阶段二：可行性报告口径修正 + 两份已对齐文档补“一期范围”说明。"""
import copy

from docx import Document
from docx.text.paragraph import Paragraph
from docx.shared import Pt

BASE = r"D:\课设\智维台"


def set_text(par, text):
    runs = par.runs
    if not runs:
        par.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


def replace_para(doc, keyword, new_text, label):
    for p in doc.paragraphs:
        if keyword in p.text:
            set_text(p, new_text)
            print("已改:", label)
            return True
    print("未找到:", label, keyword[:20])
    return False


def insert_after(doc, keyword, text, label):
    for p in doc.paragraphs:
        if keyword in p.text:
            new = copy.deepcopy(p._p)
            p._p.addnext(new)
            np = Paragraph(new, p._parent)
            set_text(np, text)
            for r in np.runs:
                r.font.size = Pt(10.5)
            print("已插入:", label)
            return True
    print("未找到插入点:", label, keyword[:20])
    return False


# ---------------------------------------------------------------- 1. 可行性报告
f = f"{BASE}\\项目可行性分析报告_智维台.docx"
doc = Document(f)
replace_para(
    doc, "本项目拟设计并实现“智维台”",
    "基于以上判断，本项目拟设计并实现“智维台”——一套面向企业 IT 服务台的智能知识协同系统。"
    "一期以对话为入口、以知识为主线、以交付为闭环：工程师用自然语言检索知识库并获得带来源的答案，"
    "需要产出物时由智能体生成报告、转换格式或发送审批邮件；工单建单、自动分派与 SLA 管理列入二期规划，不在本期交付范围内。",
    "可行性 1.2 背景（立项判断段）")
replace_para(
    doc, "本项目的总体目标是：构建一套面向企业 IT 服务台",
    "本项目的总体目标是：构建一套面向企业 IT 服务台、可私有化部署的智能知识协同系统。"
    "一期实现“对话即入口、检索即知识、交付即闭环”的业务链路（问答 → 报告生成 → 邮件审批），"
    "二期再扩展工单建单、分派与 SLA 管理；同时以可量化指标（检索命中率、首字延迟、评测通过率）验证系统可用性。",
    "可行性 2.1 项目目标")
doc.save(f)
print("saved", f)

# ---------------------------------------------------------------- 2. 测试计划
f2 = f"{BASE}\\智维台_系统测试计划.docx"
doc2 = Document(f2)
insert_after(
    doc2, "系统对外提供 19 个接口",
    "说明：本文档描述的是本期已实现范围（仓库 devSage，master@36d1d48）。工单建单、自动分派、SLA 与指标看板等能力属二期规划，"
    "不在本轮测试范围内，相应需求在《软件需求规格说明书》表 3 中标注为“二期”。",
    "测试计划 1.1 末尾")
doc2.save(f2)
print("saved", f2)

# ---------------------------------------------------------------- 3. 数据模型书
f3 = f"{BASE}\\智维台_数据模型书.docx"
doc3 = Document(f3)
insert_after(
    doc3, "本文档与《系统概要设计说明书》中的“数据视图”对应",
    "说明：本文档只描述本期已实现的持久化结构；工单、SLA、指标快照等二期实体尚未建表，待二期设计时补充。",
    "数据模型书 1.1 末尾")
doc3.save(f3)
print("saved", f3)
