import logging
import os
import time
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.agent.agent import set_checkpointer, get_checkpointer
from app.api.chat import router as chat_router, limiter
from app.api.document import router as document_router
from app.api.auth import router as auth_router
from app.api.revocation_demo import router as revocation_demo_router
from fastapi.middleware.cors import CORSMiddleware

from app.services import vector_store
from app.services.vector_store import VectorStoreService
from app.services.bm25_service import bm25_service
from app.utils.SQL_database import engine, Base
from app.utils.rabbitmq import rabbitmq
from app.config.settings import get_settings, BASE_DIR
from app.utils.logging_config import setup_logging
from app.utils.task_handler import handle_document_upload

# ── 日志系统初始化（控制台 + 按天轮转文件，见 app/utils/logging_config.py）──
cfg = get_settings()
setup_logging()
logger = logging.getLogger("rag")


async def _handle_document_upload(payload: dict):
    """消息队列异步处理文档上传任务（带幂等防护）"""
    await handle_document_upload(payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = None
    mq_connected = False

    # ── RabbitMQ 连接（可选：开发环境不可用时不阻塞启动）──
    # 注意：若首次连接失败，异步上传将禁用且不会自动恢复——aio_pika 底层连接
    # 会自动重连，但 consume() 消费者任务不会补启动，需重启服务才能启用。
    # 运维顺序：先启动 RabbitMQ / Redis，再启动后端。
    try:
        await rabbitmq.connect()
        mq_connected = True
        worker_task = asyncio.create_task(
            rabbitmq.consume(
                queue_name="document.upload.queue",
                routing_keys=["document.upload"],
                callback=_handle_document_upload,
                prefetch_count=2,
                max_retries=cfg.MQ_MAX_RETRIES,
                retry_delay=cfg.MQ_RETRY_DELAY_SECONDS,
            )
        )
        logger.info("RabbitMQ 已连接，内嵌 Worker 已启动")
    except Exception:
        logger.warning("RabbitMQ 不可用，文档异步上传功能将禁用")

    # ── 构建 BM25 索引 ──
    try:
        all_docs = VectorStoreService().get_all_documents()
    except AttributeError:
        from langchain_core.documents import Document
        all_docs = vector_store.chroma.get()
        all_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
        ]
    bm25_service.build_index(all_docs)
    Base.metadata.create_all(bind=engine)
    # 轻量迁移：users 表补充资料字段（create_all 不会为已存在的表加列）
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
        for col, ddl in (
            ("display_name", "VARCHAR DEFAULT ''"),
            ("avatar", "VARCHAR DEFAULT ''"),
            ("bio", "VARCHAR DEFAULT ''"),
        ):
            if col not in cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))
        conn.commit()
    logger.info("BM25 索引构建完成，文档数: %d", len(all_docs))

    # ── 初始化检查点 ──
    async with AsyncSqliteSaver.from_conn_string(cfg.CHECKPOINT_DIR) as saver:
        await saver.setup()
        set_checkpointer(saver)
        if get_checkpointer() is None:
            logger.error("checkpointer 注入失败")
        yield # ← FastAPI 在此运行

    # ── 关闭时：取消 Worker 并断开 ──
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    if mq_connected:
        await rabbitmq.close()


app = FastAPI(title="RAG Personal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志：方法/路径/状态码/耗时（静态资源跳过，避免刷屏）"""
    if request.url.path.startswith(("/static", "/assets", "/reports", "/avatars")):
        return await call_next(request)
    t0 = time.time()
    response = await call_next(request)
    logger.info(
        "HTTP | method=%s | path=%s | status=%d | 耗时=%.3fs",
        request.method, request.url.path, response.status_code, time.time() - t0,
    )
    return response

app.include_router(chat_router, prefix="/api/chat", tags=["对话接口"])
app.include_router(document_router, prefix="/api/document", tags=["上传文件接口"])
app.include_router(auth_router, prefix="/api/auth", tags=["用户登录注册相关接口"])
app.include_router(revocation_demo_router)


# ── 前端托管：Vue 构建产物优先，未构建时回退旧 HTML 前端 ──
VUE_DIST = BASE_DIR / "frontend/dist"
VUE_READY = (VUE_DIST / "index.html").exists()

if VUE_READY:
    app.mount("/assets", StaticFiles(directory=str(VUE_DIST / "assets")), name="assets")


@app.get("/")
async def index_page():
    """根路径：Vue 前端（构建产物）优先；未构建时回退旧 HTML 前端"""
    if VUE_READY:
        return FileResponse(str(VUE_DIST / "index.html"))
    return RedirectResponse(url="/static/index.html")


# 静态文件服务（旧 HTML 前端，保底回退）
# ── 限流（装饰器模式：chat 路由经 @limiter.limit 分别控制）──
# 注意：不挂 SlowAPIASGIMiddleware——其 send_wrapper 会对流式响应的每块 body
# 重复发送 http.response.start，触发 uvicorn "Expected ASGI message" 错误。
if cfg.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ———— 挂载静态路由 —————
app.mount("/static", StaticFiles(directory="app/static", html=True), name="static")

# 确保报告目录存在后再挂载
REPORT_DIR = BASE_DIR / "app/data/report"
os.makedirs(REPORT_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

# 确保头像目录存在后再挂载
AVATAR_DIR = BASE_DIR / "app/data/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常 | path=%s method=%s", request.url.path, request.method)
    if cfg.is_production:
        message = "服务器内部错误，请联系管理员"
    else:
        message = f"服务器内部错误: {str(exc)}"
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": message, "data": None}
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "RAG Personal API"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", reload=True)
