# -*- coding: utf-8 -*-
"""演示 PPT：智维台（OpsDesk）项目答辩（约 10 页）。"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image

BASE = r"D:\课设"
OUT = os.path.join(BASE, "交付", "智维台_答辩PPT.pptx")
IMG = os.path.join(BASE, "图片")
SHOT = os.path.join(BASE, "截图")

BLUE = RGBColor(0x2B, 0x6C, 0xB0)
DARK = RGBColor(0x1F, 0x29, 0x37)
GRAY = RGBColor(0x6B, 0x72, 0x80)
LIGHT = RGBColor(0xF3, 0xF6, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2F, 0x85, 0x5A)
ORANGE = RGBColor(0xB7, 0x79, 0x1F)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide():
    return prs.slides.add_slide(BLANK)


def tb(s, x, y, w, h, text, size=18, bold=False, color=DARK, align=PP_ALIGN.LEFT, font="微软雅黑"):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
    return box


def bar(s, x, y, w, h, color):
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def header(s, title, kicker=""):
    bar(s, 0, 0, 13.333, 0.06, BLUE)
    if kicker:
        tb(s, 0.7, 0.35, 11, 0.35, kicker, 12, False, GRAY)
        tb(s, 0.7, 0.62, 11, 0.6, title, 26, True, DARK)
    else:
        tb(s, 0.7, 0.5, 11.5, 0.7, title, 26, True, DARK)
    bar(s, 0.72, 1.35, 1.1, 0.05, BLUE)


def bullets(s, x, y, w, items, size=15, gap=0.52, marker="•", color=DARK):
    for i, (head, body) in enumerate(items):
        yy = y + i * gap
        tb(s, x, yy, 0.3, 0.4, marker, size, True, BLUE)
        tb(s, x + 0.32, yy, w - 0.32, 0.35, head, size, True, color)
        if body:
            tb(s, x + 0.32, yy + 0.3, w - 0.32, 0.4, body, size - 2.5, False, GRAY)


def pic(s, path, x, y, w=None, h=None):
    iw, ih = Image.open(path).size
    ratio = iw / ih
    if w and not h:
        h = w / ratio
    elif h and not w:
        w = h * ratio
    return s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))


def footer(s, page):
    tb(s, 0.7, 6.95, 8, 0.35, "智维台（OpsDesk）· 第 5 组 · 2026-11", 10, False, GRAY)
    tb(s, 12.2, 6.95, 0.6, 0.35, str(page), 10, False, GRAY, PP_ALIGN.RIGHT)


# ── 1 封面 ────────────────────────────────────────────────
s = slide()
bar(s, 0, 0, 13.333, 7.5, RGBColor(0x0F, 0x1A, 0x2B))
bar(s, 0, 0, 0.14, 7.5, BLUE)
tb(s, 1.1, 1.6, 10, 0.45, "广州南方学院 · 工学院 · 2026 秋季项目验收", 14, False, RGBColor(0x9C, 0xB3, 0xD1))
tb(s, 1.1, 2.05, 11, 1.0, "智维台（OpsDesk）", 46, True, WHITE)
tb(s, 1.1, 3.05, 11, 0.6, "面向企业 IT 服务台的智能知识协同系统", 22, False, RGBColor(0xC7, 0xD7, 0xEE))
bar(s, 1.12, 3.75, 1.6, 0.06, BLUE)
tb(s, 1.1, 4.05, 11, 1.2,
   "第 5 组　组长：冯嘉伟（2420220019）\n组员：杨文彬　刘文源　张琎　林景煌", 15, False, RGBColor(0x9C, 0xB3, 0xD1))
tb(s, 1.1, 6.2, 11, 0.4, "演示时间 5 分钟　|　代码仓库 github.com/orange-orunji/devSage", 12, False, RGBColor(0x64, 0x74, 0x8B))

# ── 2 项目来源与痛点 ───────────────────────────────────────
s = slide()
header(s, "项目来源：研发知识「找不到、用不上、留不住」", "一、为什么做")
bullets(s, 0.9, 1.75, 6.0, [
    ("文档散落三处", "技术规范在网盘、方案在群文件、复盘在个人笔记，无统一入口与版本"),
    ("新人上手靠问人", "同类问题反复问，老员工重复解释，知识不沉淀"),
    ("查到之后还要「手工交付」", "写周报、转格式、发邮件全手工，检索与交付之间是断的"),
])
bar(s, 7.3, 1.7, 5.1, 4.4, LIGHT)
tb(s, 7.6, 1.95, 4.6, 0.4, "调研结论（第 1 周访谈 4 人）", 14, True, BLUE)
tb(s, 7.6, 2.45, 4.5, 3.4,
   "① 知识查找占工程师日常时间首位\n\n② 答案需要「可追溯」，不能只说结论\n\n③ 对外发送属于敏感动作，必须可控\n\n④ 团队规模小，不接受重型平台与长实施周期",
   13, False, DARK)
footer(s, 2)

# ── 3 定位与范围 ──────────────────────────────────────────
s = slide()
header(s, "项目定位：一期「知识库 + 交付 Agent」", "二、做什么")
bar(s, 0.9, 1.75, 5.7, 1.5, BLUE)
tb(s, 1.15, 1.92, 5.2, 0.4, "一期（已实现）", 16, True, WHITE)
tb(s, 1.15, 2.32, 5.3, 0.8, "检索问答 · 文档入库 · 报告生成\n格式转换 · 邮件交付 · 人工审批", 13, False, WHITE)
bar(s, 6.9, 1.75, 5.5, 1.5, RGBColor(0xE2, 0xE8, 0xF0))
tb(s, 7.15, 1.92, 5.0, 0.4, "二期（规划）", 16, True, GRAY)
tb(s, 7.15, 2.32, 5.1, 0.8, "工单建单 · 自动分派 · SLA\n指标看板 · 角色权限矩阵", 13, False, GRAY)
tb(s, 0.9, 3.6, 11.5, 0.4, "一句话：让工程师用自然语言找到答案，并直接把结果交付出去。", 17, True, DARK)
bullets(s, 0.9, 4.3, 11.4, [
    ("覆盖范围", "6 个业务模块 · 22 个接口 · 7 个函数调用工具 · 1 张业务表 + 文件/向量混合存储"),
    ("边界清晰", "文档与需求一一对应一期实现状态，未实现的能力标注为二期，不做「文档里有、系统里没有」"),
], size=14, gap=0.75)
footer(s, 3)

# ── 4 技术路线与架构 ──────────────────────────────────────
s = slide()
header(s, "技术路线：五层架构 + 状态图智能体", "三、怎么做")
pic(s, os.path.join(IMG, "arch.png"), 0.7, 1.55, w=7.7)
tb(s, 8.8, 1.6, 4.0, 0.4, "关键设计决策", 14, True, BLUE)
tb(s, 8.8, 2.05, 4.0, 4.4,
   "① 分层单体：api → services → domain，adapters 实现端口，换模型只改适配器\n\n"
   "② 检索是「图上的必经节点」，不是提示词要求 —— 知识问题检索覆盖 100%\n\n"
   "③ 记忆与审批状态落在检查点，刷新、切会话、换设备都能恢复\n\n"
   "④ 前端 Vue3 由 FastAPI 托管，单进程即可演示，Docker Compose 一键部署",
   11.5, False, DARK)
footer(s, 4)

# ── 5 亮点一：检索 ────────────────────────────────────────
s = slide()
header(s, "亮点一：三阶混合检索 + 三层意图路由", "四、亮点")
bullets(s, 0.9, 1.75, 6.2, [
    ("意图路由", "正则精确标记 → 语料 IDF 稀有词 → 语义分类，三层漏斗分流"),
    ("混合召回", "HyDE 语义扩展 + BM25 关键词 + 向量，RRF 倒数排名融合"),
    ("重排兜底", "BGE 重排取 Top-3，最高分 < 0.1 自动转联网搜索并标注来源"),
    ("可量化", "300 题检索评测（Recall@1 57%）、38 题 Agent 端到端评测（38/38）"),
], size=14, gap=1.05)
bar(s, 7.4, 1.75, 5.0, 3.9, LIGHT)
tb(s, 7.65, 1.95, 4.5, 0.4, "本轮实测优化", 14, True, BLUE)
tb(s, 7.65, 2.45, 4.5, 3.0,
   "检索阶段耗时\n13.06 s  →  2.96 ~ 4.42 s\n（约 3 倍）\n\n"
   "措施：HyDE 按需启用 + BM25 与 HyDE 并行\n+ 检索结果 120 s 缓存\n\n"
   "重复检索 12.64 s  →  直接命中缓存",
   13, False, DARK)
footer(s, 5)

# ── 6 亮点二：人工审批 ────────────────────────────────────
s = slide()
header(s, "亮点二：敏感动作人工审批，可中断可恢复", "四、亮点")
pic(s, os.path.join(SHOT, "shot_approval.png"), 0.75, 1.7, w=7.6)
tb(s, 8.7, 1.75, 4.0, 0.4, "怎么做的", 14, True, BLUE)
tb(s, 8.7, 2.2, 4.0, 4.2,
   "· 工具执行前 interrupt 挂起，前端弹出审批卡片\n\n"
   "· 卡片列出收件人、主题、正文，用户确认后才真正发送\n\n"
   "· 状态写入检查点：刷新、切会话、换设备都能恢复\n\n"
   "· 审批期间输入区锁定，防重复提交\n\n"
   "价值：把「AI 会不会乱发邮件」变成可解释、可拦截、可追溯",
   12, False, DARK)
footer(s, 6)

# ── 7 亮点三：交付闭环 ────────────────────────────────────
s = slide()
header(s, "亮点三：从检索到交付的闭环", "四、亮点")
pic(s, os.path.join(SHOT, "shot_report.png"), 0.75, 1.7, w=7.6)
tb(s, 8.7, 1.75, 4.0, 0.4, "一次对话完成交付", 14, True, BLUE)
tb(s, 8.7, 2.2, 4.0, 4.2,
   "· 检索知识库 → 汇总 → 生成结构化周报\n\n"
   "· 可转 Word、可下载、可邮件发送（走审批）\n\n"
   "· 报告附带引用来源，注明数据取自哪份文档\n\n"
   "右图实际生成内容还主动指出了\n「3 组重复文档、3 个测试残留文件」，\n"
   "说明它真的在读库、而不是套模板",
   12, False, DARK)
footer(s, 7)

# ── 8 系统演示 ────────────────────────────────────────────
s = slide()
header(s, "系统演示：5 分钟看五个场景", "五、演示")
pic(s, os.path.join(SHOT, "shot_chat_qa.png"), 0.75, 1.7, w=7.4)
tb(s, 8.55, 1.7, 4.2, 0.4, "演示顺序", 14, True, BLUE)
tb(s, 8.55, 2.15, 4.2, 4.3,
   "① 登录 → 工作台（会话与统计）\n\n"
   "② 提问 → 流式回答 + 引用来源\n\n"
   "③ 生成周报 → 下载\n\n"
   "④ 发邮件 → 审批卡片 → 确认\n\n"
   "⑤ 文档管理 → 指标看板 → 删除（管理员）\n\n"
   "演示账号已设为管理员，现场可完整走通",
   12, False, DARK)
footer(s, 8)

# ── 9 工程质量 ────────────────────────────────────────────
s = slide()
header(s, "工程质量：可测、可部署、可追溯", "六、质量")
cards = [
    ("25", "接口级用例", "16 通过 / 4 未执行"),
    ("5", "发现缺陷", "1 个已修复关闭"),
    ("22", "对外接口", "19 原有 + 3 新增"),
    ("92", "人天投入", "5 人 × 约 3 个月"),
]
for i, (num, label, sub) in enumerate(cards):
    x = 0.9 + i * 3.05
    bar(s, x, 1.75, 2.75, 1.55, LIGHT)
    tb(s, x + 0.18, 1.85, 2.4, 0.6, num, 30, True, BLUE)
    tb(s, x + 0.18, 2.45, 2.4, 0.35, label, 13, True, DARK)
    tb(s, x + 0.18, 2.8, 2.4, 0.4, sub, 10.5, False, GRAY)
bullets(s, 0.9, 3.7, 11.4, [
    ("测试：先用后测", "25 条接口用例真跑真记，缺陷带复现与证据（results.json 可查）"),
    ("部署：两条路都通", "Docker Compose 四容器；本机单进程亦可演示，队列缺失时上传自动降级"),
    ("文档：与代码同仓库", "11 件交付文档 + 生成脚本 + 执行证据同仓管理，改口径可一键重生成"),
], size=13.5, gap=0.85)
footer(s, 9)

# ── 10 分工 ──────────────────────────────────────────────
s = slide()
header(s, "团队分工：5 人各管一摊", "七、团队")
rows = [("冯嘉伟 2420220019", "组长 · 总体架构/接口/文档统稿", "1.10"),
        ("杨文彬 2420160092", "检索与生成：路由、混合召回、重排、评测", "1.00"),
        ("刘文源 2420160053", "文档与数据：上传解析、入库、数据模型", "1.00"),
        ("张琎 2420160099", "前端与交互：工作台、审批卡片、文档管理页", "0.95"),
        ("林景煌 2410310023", "部署与质量：容器编排、worker、测试执行", "0.95")]
tb(s, 0.9, 1.7, 3.0, 0.35, "成员", 12, True, GRAY)
tb(s, 4.3, 1.7, 6.5, 0.35, "负责模块与主要工作", 12, True, GRAY)
tb(s, 11.4, 1.7, 1.2, 0.35, "贡献度", 12, True, GRAY)
for i, (who, what, ratio) in enumerate(rows):
    y = 2.12 + i * 0.78
    bar(s, 0.9, y + 0.66, 11.6, 0.02, RGBColor(0xE5, 0xE7, 0xEB))
    tb(s, 0.9, y, 3.2, 0.35, who, 13, True, DARK)
    tb(s, 4.3, y, 6.8, 0.5, what, 12, False, DARK)
    tb(s, 11.4, y, 1.2, 0.35, ratio, 13, True, BLUE)
tb(s, 0.9, 6.15, 11.5, 0.4, "贡献度均值 1.00，合计 5.00；组长承担统稿与答辩主讲", 11, False, GRAY)
footer(s, 10)

# ── 11 不足与规划 ────────────────────────────────────────
s = slide()
header(s, "不足、二期规划与致谢", "八、总结")
bullets(s, 0.9, 1.7, 6.3, [
    ("首字延迟未达标", "中位 6.6 s（目标 3 s），瓶颈在模型 TTFT，需换模型或改流式策略"),
    ("空输入与错误码", "空问题未校验、鉴权失败返回 400、错误格式不统一，均已列入缺陷"),
    ("二期：工单闭环", "建单 → 分派 → SLA → 看板，与知识库打通，形成完整服务台"),
], size=13.5, gap=1.25)
bar(s, 7.6, 1.7, 4.8, 3.5, LIGHT)
tb(s, 7.85, 1.9, 4.3, 0.4, "谢谢，欢迎提问", 20, True, BLUE)
tb(s, 7.85, 2.5, 4.3, 2.4,
   "代码与文档：\ngithub.com/orange-orunji/devSage\n\n"
   "11 件验收材料 + 全部源码\n均在同仓 master 分支", 12.5, False, DARK)
bar(s, 0.9, 5.6, 11.6, 0.04, RGBColor(0xE5, 0xE7, 0xEB))
tb(s, 0.9, 5.75, 11.5, 0.9,
   "「让工程师用自然语言找到答案，并直接把结果交付出去」—— 一期做到了检索与交付，二期补上工单闭环。",
   14, True, DARK)
footer(s, 11)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs.save(OUT)
print("saved:", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
