# -*- coding: utf-8 -*-
"""数据模型书插图：ER 图。"""
import os

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
OUT = r"D:\课设\图片\er.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

W, H = 1400, 1010
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
_f = {}


def F(sz):
    if sz not in _f:
        _f[sz] = ImageFont.truetype(FONT, sz)
    return _f[sz]


INK = "#1f2937"
GRAY = "#6b7280"
BLUE = "#2b6cb0"
BLUE_BG = "#e8f0fa"
GREEN = "#2f855a"
GREEN_BG = "#e6f4ea"
AMBER = "#b7791f"
AMBER_BG = "#fdf3e2"
LINE = "#4a5568"


def entity(x, y, w, h, name, sub, fields, fill, outline):
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill="white", outline=outline, width=3)
    d.rounded_rectangle([x, y, x + w, y + 40], radius=8, fill=fill, outline=outline, width=3)
    d.text((x + w / 2, y + 20), name, font=F(21), fill=INK, anchor="mm")
    d.text((x + w / 2, y + 56), sub, font=F(14), fill=GRAY, anchor="mm")
    yy = y + 78
    for f in fields:
        d.text((x + 16, yy), f, font=F(15), fill=INK, anchor="lm")
        yy += 24


def arrow(p1, p2, label, both=False):
    d.line([p1, p2], fill=LINE, width=2)
    import math
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for tip in ([p2] if not both else [p1, p2]):
        a = ang if tip is p2 else ang + math.pi
        L = 12
        d.polygon([tip,
                   (tip[0] - L * math.cos(a - 0.4), tip[1] - L * math.sin(a - 0.4)),
                   (tip[0] - L * math.cos(a + 0.4), tip[1] - L * math.sin(a + 0.4))], fill=LINE)
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    tw = d.textlength(label, font=F(14))
    d.rectangle([mx - tw / 2 - 4, my - 11, mx + tw / 2 + 4, my + 11], fill="white")
    d.text((mx, my), label, font=F(14), fill=GRAY, anchor="mm")


# 左列：用户 → 会话 → 消息 → 引用
entity(60, 70, 330, 190, "users 用户", "SQLite · app.db", ["PK id", "username (UK)", "hashed_password", "display_name / avatar"], BLUE_BG, BLUE)
entity(60, 300, 330, 190, "session 会话", "文件 · chat_history/<uid>", ["PK session_id", "FK user_id", "title / pinned", "created_at"], GREEN_BG, GREEN)
entity(60, 530, 330, 190, "message 消息", "会话文件内容", ["PK message_id", "FK session_id", "role (human/assistant)", "content"], GREEN_BG, GREEN)
entity(60, 760, 330, 150, "citation 引用", "消息内嵌字段", ["FK message_id", "doc_name / chunk_id"], "#f3f4f6", "#94a3b8")

# 右列：文档 → 切片；检查点；审批
entity(900, 70, 430, 190, "document 文档", "目录 + 统计接口", ["PK doc_id", "name / type / size", "chunk_count", "FK uploaded_by"], AMBER_BG, AMBER)
entity(900, 300, 430, 190, "chunk 切片", "Chroma 向量库", ["PK chunk_id", "FK doc_id / seq", "text", "embedding (vector)"], AMBER_BG, AMBER)
entity(900, 530, 430, 190, "checkpoint 检查点", "SQLite · checkpoints.db", ["PK thread_id / checkpoint_id", "FK session_id", "state (JSON)", "writes 表记录中间写入"], "#f3f4f6", "#94a3b8")
entity(900, 760, 430, 150, "approval 待审批", "会话内 pending 状态", ["FK session_id", "action / payload", "status"], "#f3f4f6", "#94a3b8")

arrow((225, 260), (225, 300), "1 : N")
arrow((225, 490), (225, 530), "1 : N")
arrow((225, 720), (225, 760), "1 : N")
arrow((390, 110), (900, 110), "1 : N 上传")
arrow((1115, 260), (1115, 300), "1 : N 切片")
arrow((390, 350), (900, 600), "1 : N 检查点")
arrow((390, 690), (900, 800), "1 : N 审批")

d.text((700, 968), "说明：蓝色为关系型实体，绿色为会话域（文件存储），橙色为知识域（目录 + 向量库），灰色为支撑实体。",
       font=F(15), fill=GRAY, anchor="mm")
img.save(OUT, dpi=(200, 200))
print("saved", OUT, img.size)
