# -*- coding: utf-8 -*-
"""《数据模型书》—— 智维台（DevSage）"""
import os
import sys

sys.path.insert(0, r"D:\课设\_lib")
import dlib

OUT = r"D:\课设\智维台\智维台_数据模型书.docx"
doc = dlib.new_doc()
c = dlib.Counter()

# ------------------------------------------------------------------ 封面
doc.add_paragraph()
p_ = doc.add_paragraph()
p_.alignment = 1
p_.add_run().add_picture(r"D:\课设\_lib\logo.png", width=dlib.Cm(3.2))
for _ in range(2):
    dlib.cover_line(doc, "", 12)
dlib.cover_title(doc, "数据模型书", 30)
dlib.cover_line(doc, "", 14)
dlib.cover_line(doc, "智维台（OpsDesk）智能知识库与工单协同系统", 16, space=10)
dlib.cover_line(doc, "（代码仓库 devSage，被测环境 http://127.0.0.1:9000）", 11, space=30)
dlib.cover_line(doc, "项目组：第 5 组　　组长：冯嘉伟（2420220019）", 14, space=8)
dlib.cover_line(doc, "版本号：V1.0　　日期：2026 年 11 月 20 日", 14, space=8)
dlib.page_break(doc)

# ------------------------------------------------------------------ 核准签名
dlib.h1(doc, "核准签名")
dlib.table(doc, c, "文档核准签名", ["角色", "姓名", "职责", "签名", "日期"],
           [["编写", "冯嘉伟", "数据模型梳理、ER 图与表结构", "", "2026-11-20"],
            ["审核", "刘文源", "核对字段与建表脚本一致性", "", "2026-11-20"],
            ["批准", "指导教师", "文档合规性与完整性", "", ""]],
           [2.2, 3.0, 6.4, 3.4, 2.6], center=(0, 4))

# ------------------------------------------------------------------ 修订历史
dlib.h1(doc, "修订历史")
dlib.table(doc, c, "修订记录", ["版本号", "变更日期", "主要变更内容", "变更人"],
           [["V0.1", "2026-11-18", "整理实体清单，绘制初版 ER 图", "冯嘉伟"],
            ["V0.8", "2026-11-19", "补充 users 表结构与文件存储结构，核对真实库", "刘文源"],
            ["V1.0", "2026-11-20", "补充 SQL 与向量库配置脚本，定稿", "全组"]],
           [1.8, 2.8, 7.6, 2.6], center=(0, 1))

# ------------------------------------------------------------------ 1 概述
dlib.h1(doc, "1  概述")
dlib.h2(doc, "1.1  定义")
dlib.p(doc, "数据模型书（Data Model Document）是描述系统数据实体、属性、实体间联系及其物理落盘方式的文档。本文档定义智维台系统在持久化层的事实模型：哪些数据存在关系型数据库、哪些以文件形式存储、哪些存放在向量库，以及它们之间的引用关系。")
dlib.p(doc, "本文档与《系统概要设计说明书》中的“数据视图”对应，是建库脚本、后端 ORM 定义与测试数据准备的依据；所有字段均以运行环境中的真实结构为准（app/app.db、app/data/ 与 Chroma 持久化目录）。")
dlib.h2(doc, "1.2  目的")
dlib.p(doc, "（1）为开发人员提供唯一的字段口径，避免前后端各自命名；（2）为测试人员提供数据校验依据（如注册后应新增一行、上传后切片数应增加）；（3）为验收与后续维护提供数据资产清单；（4）记录“关系型 + 文件 + 向量”三种存储的分工，防止把本应入库的数据写成文件。")
dlib.h2(doc, "1.3  缩写")
dlib.table(doc, c, "缩略语", ["缩写", "全称", "说明"],
           [["PK", "Primary Key", "主键"],
            ["FK", "Foreign Key", "外键或逻辑外键（文件中以字段引用）"],
            ["UK", "Unique Key", "唯一约束"],
            ["JSON", "JavaScript Object Notation", "文件存储的序列化格式"],
            ["Chroma", "Chroma DB", "本地向量数据库，持久化切片嵌入"],
            ["Embedding", "向量嵌入", "文本经模型编码得到的定长向量"]],
           [2.9, 3.8, 7.9], center=(0,), first_bold=True)
dlib.h2(doc, "1.4  参考资料")
dlib.table(doc, c, "参考资料", ["文档名称", "来源", "用途"],
           [["系统概要设计说明书 V1.0", "本项目组", "数据视图与模块划分"],
            ["系统详细设计说明书 V1.0", "本项目组", "接口与字段定义"],
            ["SQLAlchemy 2.0 文档", "官方文档", "ORM 映射与建表"],
            ["Chroma 官方文档", "官方文档", "集合结构与元数据过滤"],
            ["LangGraph 持久化文档", "官方文档", "checkpoints 表结构"]],
           [6.2, 4.4, 4.0], first_bold=True)

# ------------------------------------------------------------------ 2 数据模型
dlib.h1(doc, "2  数据模型")
dlib.h2(doc, "2.1  ER 图")
dlib.p(doc, "系统共有 8 个核心数据实体，按存储介质分为三类：关系型实体（users）、会话域实体（session / message / citation，落在 app/data/chat_history/ 下的文件中）、知识域实体（document 元数据与 chunk 切片，分别落在文件目录与 Chroma 向量库），另有 checkpoint 与 approval 两个支撑实体。实体关系如图 1 所示。")
dlib.figure(doc, c, r"D:\课设\图片\er.png", "系统 ER 图（按存储介质着色）", 15.2)
dlib.p(doc, "主要联系：一个用户拥有多个会话（1:N）；一个会话包含多条消息（1:N）；一条消息可携带多条引用（1:N）；一个用户可上传多个文档（1:N）；一个文档切分为多个切片（1:N）；一个会话对应多条检查点记录（1:N），用于审批中断后的恢复；一个会话可产生多条待审批记录（1:N）。")
dlib.p(doc, "设计取舍说明：会话与消息未落关系库，而是按用户维度存为文件，原因是消息体包含大段 Markdown 与引用数组，读写以“整段会话”为单位、无跨会话的关联查询需求；切片向量同理，交由向量库托管，只在文档元数据中保留 chunk_count 统计。这一取舍使主库保持极小（仅 1 张表），但也带来“统计需遍历文件”的代价，需在测试中专门校验统计口径。")

dlib.h2(doc, "2.2  数据表描述")
dlib.table(doc, c, "数据集合清单", ["序号", "数据集合", "存储介质", "主键", "说明"],
           [["1", "users", "SQLite（app/app.db）", "id", "用户账号与资料，11 行（截至 2026-11-20）"],
            ["2", "session", "文件（app/data/chat_history/<uid>）", "session_id", "会话元数据：标题、置顶、创建时间"],
            ["3", "message", "同上（会话文件内的数组）", "message_id", "消息：角色、内容、引用"],
            ["4", "citation", "内嵌于 message", "—", "引用片段：文档名、片段号、得分"],
            ["5", "document", "文件目录 + 统计接口", "doc_id", "上传文档的原件与元数据，9 篇"],
            ["6", "chunk", "Chroma 向量库", "chunk_id", "切片正文与向量，39 条"],
            ["7", "checkpoint", "SQLite（app/data/checkpoints.db）", "thread_id + checkpoint_id", "智能体运行状态快照"],
            ["8", "approval", "会话文件的 pending 字段", "—", "待审批动作与结论"]],
           [1.1, 2.6, 5.4, 3.0, 3.1], center=(0,), first_bold=True)

dlib.h2(doc, "2.3  数据表结构")
dlib.h3(doc, "2.3.1  users 表（关系型，真实结构）")
dlib.table(doc, c, "users 表结构", ["字段", "类型", "约束", "默认值", "说明"],
           [["id", "INTEGER", "PK, 自增", "—", "用户主键"],
            ["username", "VARCHAR", "UK, 非空", "—", "登录名，唯一索引 ix_users_username"],
            ["hashed_password", "VARCHAR", "非空", "—", "口令哈希（bcrypt），不存明文"],
            ["display_name", "VARCHAR", "可空", "''", "显示名，用于界面问候语"],
            ["avatar", "VARCHAR", "可空", "''", "头像相对路径（/avatars/…）"],
            ["bio", "VARCHAR", "可空", "''", "个人简介"]],
           [3.0, 2.4, 3.2, 2.2, 4.8], center=(0, 3), first_bold=True)

dlib.h3(doc, "2.3.2  session / message 文件结构（会话域）")
dlib.p(doc, "会话历史按用户分文件存储，文件名即用户 ID；文件内容为该用户全部会话的结构化记录。字段定义如表 8、表 9 所示。")
dlib.table(doc, c, "session 结构", ["字段", "类型", "必填", "说明"],
           [["session_id", "string", "是", "会话唯一标识，前端创建时生成"],
            ["user_id", "string", "是", "所属用户，来自令牌"],
            ["title", "string", "否", "会话标题，默认“新会话”，可重命名"],
            ["pinned", "bool", "否", "是否置顶（前端按用户隔离存 localStorage）"],
            ["created_at / updated_at", "ISO8601", "是", "创建与最后活跃时间"],
            ["pending", "object", "否", "待审批动作：action / payload / status"]],
           [4.0, 3.0, 1.6, 6.0], center=(1, 2), first_bold=True)
dlib.table(doc, c, "message 结构", ["字段", "类型", "必填", "说明"],
           [["message_id", "string", "是", "消息标识，前端用于流式占位"],
            ["session_id", "string", "是", "所属会话"],
            ["role", "string", "是", "human / assistant"],
            ["content", "string", "是", "Markdown 正文，含流式合并后的完整答案"],
            ["citations", "array", "否", "引用数组：doc_name、chunk_id、score"],
            ["created_at", "ISO8601", "是", "消息时间"]],
           [4.0, 3.0, 1.6, 6.0], center=(1, 2), first_bold=True)

dlib.h3(doc, "2.3.3  document / chunk 结构（知识域）")
dlib.table(doc, c, "document 元数据", ["字段", "类型", "必填", "说明"],
           [["doc_id", "string", "是", "文档标识，入库时生成"],
            ["name / type / size", "string / string / int", "是", "文件名、扩展名（txt/docx/pdf/md）、字节数"],
            ["chunk_count", "int", "是", "切片数量，文档统计接口返回"],
            ["uploaded_by", "string", "是", "上传者 user_id"],
            ["uploaded_at", "ISO8601", "是", "入库时间"],
            ["status", "string", "是", "parsing / ready / failed"]],
           [4.0, 4.0, 1.6, 5.0], center=(2,), first_bold=True)
dlib.table(doc, c, "chunk 集合（Chroma）", ["字段", "类型", "说明"],
           [["id", "string", "切片主键，形如 docId_seq"],
            ["document", "string", "切片正文（Chroma 内嵌存储）"],
            ["metadata", "object", "doc_id、seq、doc_name、uploaded_at，用于过滤与引用回填"],
            ["embedding", "float[ ]", "文本向量，由 Embedding 模型生成，维度随模型而定"]],
           [3.4, 3.4, 7.4], center=(0,), first_bold=True)

dlib.h3(doc, "2.3.4  checkpoint 表（智能体状态）")
dlib.table(doc, c, "checkpoint 结构（LangGraph 持久化）", ["表/字段", "类型", "说明"],
           [["checkpoints.thread_id", "TEXT", "会话线程标识，与 session_id 对应"],
            ["checkpoints.checkpoint_id", "TEXT", "检查点编号，按执行步递增"],
            ["checkpoints.state", "BLOB/JSON", "消息数组与工具调用状态快照"],
            ["writes", "TEXT", "中间写入记录，用于中断恢复与去重"],
            ["metadata", "JSON", "来源、步骤、父检查点"]],
           [5.0, 3.4, 5.8], center=(0,), first_bold=True)

dlib.h2(doc, "2.4  数据表 SQL 脚本")
dlib.h3(doc, "2.4.1  users 建表与索引")
dlib.code(doc, """-- 与 app/app.db 中的真实结构一致（SQLite）
CREATE TABLE users (
    id              INTEGER NOT NULL,
    username        VARCHAR,
    hashed_password VARCHAR,
    display_name    VARCHAR DEFAULT '',
    avatar          VARCHAR DEFAULT '',
    bio             VARCHAR DEFAULT '',
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE INDEX        ix_users_id       ON users (id);""")
dlib.h3(doc, "2.4.2  会话与消息的存储约定（JSON）")
dlib.code(doc, """// app/data/chat_history/<user_id>
{
  "sessions": [
    {
      "session_id": "demo_student_b5f72d08",
      "title": "知识库文档查询与上传",
      "created_at": "2026-11-20T20:10:12",
      "updated_at": "2026-11-20T20:12:40",
      "messages": [
        {"message_id": "m1", "role": "human",
         "content": "这个知识库现在收录了哪些文档？",
         "created_at": "2026-11-20T20:10:12"},
        {"message_id": "m2", "role": "assistant",
         "content": "当前知识库共 9 篇文档……",
         "citations": [{"doc_name": "smoke_upload.txt", "chunk_id": "c1", "score": 0.82}],
         "created_at": "2026-11-20T20:10:19"}
      ]
    }
  ]
}""")
dlib.h3(doc, "2.4.3  向量库集合创建（Chroma）")
dlib.code(doc, """import chromadb
client = chromadb.PersistentClient(path="app/data/chroma")
col = client.get_or_create_collection(
    name="knowledge_chunks",
    metadata={"hnsw:space": "cosine"}     # 余弦距离，配合归一化向量
)
col.add(ids=["doc1_0", "doc1_1"],
        documents=["切片正文……", "切片正文……"],
        metadatas=[{"doc_id": "doc1", "seq": 0}, {"doc_id": "doc1", "seq": 1}],
        embeddings=[[0.01, -0.23, ...], [0.07, 0.11, ...]])""")
dlib.h3(doc, "2.4.4  一致性校验脚本（供测试使用）")
dlib.p(doc, "为验证“文档数 / 切片数 / 会话数”三个口径一致，测试阶段使用下面这段脚本做交叉核对：users 行数与注册数一致、文档统计与目录文件数一致、切片统计与向量库条数一致。")
dlib.code(doc, """import sqlite3, os, glob, requests
db = sqlite3.connect(r"app/app.db")
users = db.execute("select count(*) from users").fetchone()[0]

base = "http://127.0.0.1:9000"
h = {"Authorization": f"Bearer {token}"}
stats = requests.get(f"{base}/api/document/stats", headers=h).json()

files = len(glob.glob("app/data/uploads/*"))
print("users", users, "docs", stats, "files", files)""")

dlib.add_page_numbers(doc)
doc.save(OUT)
print("saved:", OUT, "tables", len(doc.tables))
