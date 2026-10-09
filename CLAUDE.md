@PROJECT_CONTEXT.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

DevSage · 研发智库（本地目录 `RAG_Personal`）：面向研发团队的技术知识库 Agent。FastAPI + LangGraph（自定义 StateGraph）+ Vue 3 + Chroma + RabbitMQ + Redis。文档中文撰写，新写的文档/注释/提交信息请保持中文。

`PROJECT_CONTEXT.md`（AI 协作者上下文）已通过文件开头的 `@` 导入在每次会话自动加载；`README.md` 含完整架构图、更新日志、路线图。**项目当前处于冻结期（v1.13.1）**：不重做、不加功能，只做增量改造与缺陷修复；大改动先给方案对比与取舍，重大决策记录到 `docs/decision-log.md`。

## 常用命令

```bash
# 启动后端（单进程托管 API + 内嵌 Worker + 前端产物），访问 http://127.0.0.1:8000
python main.py
python -m uvicorn main:app --port 9000        # 端口被占用时换端口

# 前端（Vue 3 + Vite）
cd frontend && npm run build                  # 构建产物由 FastAPI 托管（frontend/dist）
cd frontend && npm run dev                    # 开发模式：5173 端口，/api 与 /reports 代理到 8000

# 下载 Reranker 模型（BAAI/bge-reranker-base → models/，走 hf-mirror）
python downLoad_models.py

# Docker 一键部署（Redis + RabbitMQ + Worker + API，应用在 8001）
docker compose up -d --build

# 更换 EMBEDDING_MODEL 后必须全量重建知识库
python -m app.rebuild_kb
```

## 跑测试

```bash
# 完整命令（项目根目录、bash 下）
env -u OPENAI_API_KEY PYTHONIOENCODING=utf-8 _clean_venv/Scripts/python.exe -m pytest -v

# 跑单个测试
env -u OPENAI_API_KEY PYTHONIOENCODING=utf-8 _clean_venv/Scripts/python.exe -m pytest tests/test_smoke_p0.py::test_bm25_service_handles_empty_corpus -v
```

- **必须用干净解释器 `_clean_venv`，不能用 `.venv`**：`.venv` 里装着 `langgraph-checkpoint-sqlite`，会让第一条测试（P0-1）虚假通过，掩盖要复现的缺陷
- **必须清掉 `OPENAI_API_KEY` 环境变量**：否则 P0-2 的复现前提被破坏
- `PYTHONIOENCODING=utf-8` 只为中文 Windows 控制台输出不乱码，不影响测试结果

当前 5 条测试对应的 5 个 P0 缺陷（详见 `tests/test_smoke_p0.py` 各测试 docstring）：

| 测试 | 对应 P0 缺陷 |
|------|-------------|
| `test_langgraph_sqlite_checkpointer_available` | P0-1：requirements.txt 未声明 `langgraph-checkpoint-sqlite`，干净环境按依赖清单装完启动即崩（main.py 导入 `AsyncSqliteSaver` 时 ModuleNotFoundError） |
| `test_vector_store_imports_without_openai_key` | P0-2：vector_store 在 import 阶段创建 OpenAI 客户端，进程无 `OPENAI_API_KEY` 时「只是 import 一下」就炸 |
| `test_bm25_service_handles_empty_corpus` | P0-3：BM25 service 层缺空语料守卫，空知识库（冷启动合法状态）建索引直接 ZeroDivisionError |
| `test_settings_have_safe_defaults` | P0-4：settings 把开发机内网 IP 硬编码为 `RABBITMQ_HOST` 默认值，其它机器部署会静默连向不存在的 RabbitMQ |
| `test_requirements_files_are_portable` | P0-5：requirements 文件含非 ASCII 字符且无 UTF-8 BOM，中文 Windows 上 pip 按 GBK 解码直接 UnicodeDecodeError |

## 评测（Agent 端到端 / 检索层）

```powershell
# 一键重测（PowerShell）：停旧服务 → 在 8010 端口启动最新代码 → 等就绪 → 清缓存 → 重跑
.\scripts\rerun.ps1 7,8,9        # 只重跑第 7/8/9 题
.\scripts\rerun.ps1              # 全量 38 题

# 维护
python scripts\maintenance.py clear-cache      # 清 Redis 缓存（清后建议重启服务）
python scripts\maintenance.py retry 7,8,9      # 管理评测断点
```

- `python app/eval_agent.py`：Agent 端到端 38 题五分类评测（目标 `http://127.0.0.1:8010`，注册用户 test/123456；内置 8 req/min 节流以避开服务端 10/min 限流；断点续跑落盘 `eval_agent_checkpoint.json`）
- `python app/eval_retrieval.py`：检索层 Recall@K / MRR（300 条分类评测集 `app/eval_questions.json`）
- `python app/eval_router.py`：查询意图路由器校准
- 基线 38/38（100%）；改动 Agent 相关代码后用 `rerun.ps1` 回归

## 架构大图

单进程 FastAPI（`main.py`）承载一切：API 路由 + 内嵌 RabbitMQ Worker + 静态前端托管。lifespan 中完成：RabbitMQ 连接与 Worker 启动 → BM25 全量索引重建 → SQLite 轻量迁移 → `AsyncSqliteSaver` checkpointer 注入。

### Agent 图（`app/agent/agent.py`，核心）

自定义 `StateGraph`（非预置 create_react_agent）：

```
START → reset（每轮上下文重置，防跨轮残留）
      → 条件路由 router：寒暄/动作类跳过检索；其余强制 retrieve
      → retrieve（前置检索硬约束；Rerank 分数落 metadata，阈值 ≥0.1 过滤低质结果）
      → 条件路由：检索质量不足 → web（博查联网兜底，回答带 URL/日期标注）→ agent
      → agent ⇄ tools ReAct 工具循环
```

7 个工具在 `app/services/tools/`：search / upload / delete / get_document_status（统计+报告+转换+邮件在 `status_tool.py`）/ web_search（`web_search_tool.py` 纯函数 + @tool 双层复用，图节点与工具共用）。`send_email` 执行前 `interrupt()` 人工审批：SSE 中断帧 → 前端审批卡片 → `POST /api/chat/.../resume` 恢复；`/pending` 查询待审批。审批状态存于 checkpointer，刷新/换设备可恢复。

### 检索链路（入口 `app/services/hyde.py::adaptive_retrieve`）

查询意图路由三层漏斗（`app/services/tools/query_router.py`）：正则精确标记 → 语料 IDF 稀有词信号 → 默认 semantic。semantic → HyDE + 向量 + Rerank 单路；keyword → HyDE 向量 + BM25（jieba 分词，`bm25_service.py` 模块级单例）双路 RRF 融合 → BGE-Reranker 重排序。

### 缓存一致性（`app/utils/semantic_cache.py` 等）

双层缓存：Redis MD5 精确匹配 + 内存语义相似缓存（LRU 200 条）。两条不可破坏的约束：动作指令（删除/上传/发送等）**读侧拦截跳过缓存**；工具调用轮**写侧不写缓存**。记忆类问句另有三层防御（读侧拦截 + 写侧不缓存 + 跳过前置检索）。破坏任一条会复现"假成功/状态陈旧"缺陷。

### 数据与持久化

- 向量库 Chroma（`app/data/storage/`）+ MD5 去重记录；BM25 索引内存态，启动时重建
- 会话记忆两套并存：LangGraph Checkpointer（`app/data/checkpoints.db`，thread_id 按"用户+会话"隔离，重启不丢）+ JSON 对话历史文件（`app/data/chat_history/`，历史注入为增量模式防重复）
- 异步上传链路：上传 → MD5 去重 → 文件内容 Redis 暂存（600s）→ RabbitMQ Topic 交换机 → 内嵌 Worker 消费（解析→分块→向量化→入库）→ task_id 轮询状态

### 配置（`app/config/settings.py`）

pydantic-settings 读根目录 `.env`（`SILICON_API_KEY` 必填；路径类默认值全部基于 `BASE_DIR`，**不要硬编码开发机内网 IP**）。聊天接口限流 10/min（slowapi，压测时用 `RATE_LIMIT_ENABLED=false` 关闭）。

## 已知约束与坑

- **启动顺序**：先 RabbitMQ/Redis 再启动后端；RabbitMQ 首次连接失败后异步上传禁用且不会自动恢复，需重启后端
- **requirements 文件必须纯 ASCII 或带 UTF-8 BOM**：中文 Windows 的 pip 按 GBK 解码，含中文注释且无 BOM 会直接 UnicodeDecodeError（tests 里有 P0-5 守护此约束）
- 前端源码改动后需 `npm run build` 才会被 FastAPI 托管；未构建时回退旧 HTML 前端（`app/static/index.html`）
- 旧 Streamlit 前端 `app/ui.py` 保留可用（依赖 `requirements-ui.txt`）
