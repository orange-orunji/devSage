import asyncio
import logging
from pathlib import Path

from app.config.settings import get_settings
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService
from app.services.document import _extract_text
from app.services.bm25_service import bm25_service
from app.utils.redis_client import get_redis
from app.utils.task_status import TaskTracker, TaskStatus
from app.services.vector_store import vector_store_service as vs_svc
from app.utils.logging_config import setup_logging


cfg = get_settings()
setup_logging()  # 幂等：主进程已初始化时直接复用
logger = logging.getLogger("rag.worker")

# 复用单例：每次 new 都会重新初始化 Chroma 连接，高频上传时开销大
_kb_service = KnowledgeBaseService()

# ── BM25 防抖：5 秒内多次上传只重建一次 ──
_rebuild_task: asyncio.Task | None = None
_rebuild_lock = asyncio.Lock()


async def _schedule_bm25_rebuild():
    """延迟 5 秒重建 BM25，连续上传时自动合并"""
    global _rebuild_task
    async with _rebuild_lock:
        if _rebuild_task and not _rebuild_task.done():
            _rebuild_task.cancel()
        _rebuild_task = asyncio.create_task(_do_rebuild())


async def _do_rebuild():
    await asyncio.sleep(5)
    try:
        all_docs = vs_svc.get_all_documents()
        bm25_service.build_index(all_docs)
        logger.info("BM25 索引重建完成 | 文档数=%d", len(all_docs))
    except Exception:
        logger.exception("BM25 索引重建失败")


async def _process_content(task_id: str, filename: str, content: bytes, user_id: str) -> None:
    """真正的处理逻辑：解析 → 入库 → 重建索引 → 更新任务状态。

    队列消费与同步兜底共用本函数，保证两条路径行为一致。
    """
    TaskTracker.set_status(task_id, TaskStatus.PROCESSING)
    logger.info("开始处理文档 | task_id=%s | filename=%s", task_id, filename)
    suffix = Path(filename).suffix.lower()
    text = await _extract_text(content, suffix)
    if not text.strip():
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容为空"})
        return
    kb_service = _kb_service
    kb_service.upload_by_str(text, filename, user_id=user_id)
    # 防抖重建：5 秒内多次上传只触发一次 BM25 全量重建
    await _schedule_bm25_rebuild()
    TaskTracker.set_status(task_id, TaskStatus.COMPLETED, {"filename": filename})
    logger.info("文档处理完成 | task_id=%s", task_id)


async def process_document_inline(task_id: str, filename: str, content: bytes, user_id: str) -> None:
    """队列不可用时的兜底：在本进程直接处理，保证上传功能不中断。"""
    try:
        logger.warning("队列不可用，转为同步处理 | task_id=%s | filename=%s", task_id, filename)
        await _process_content(task_id, filename, content, user_id)
    except Exception:
        logger.exception("同步处理失败 | task_id=%s", task_id)
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文档处理失败，请稍后重试"})


async def handle_document_upload(payload: dict):
    """消息队列异步处理文档上传任务（内嵌 Worker，带幂等防护）"""
    task_id = payload["task_id"]
    filename = payload["filename"]
    user_id = payload.get("user_id", "system")

    # ── 幂等性检查 ──
    idempotent_key = f"task:processed:{task_id}"
    redis = get_redis()
    if redis and redis.exists(idempotent_key):
        logger.warning("重复消息已跳过 | task_id=%s", task_id)
        return

    content_hex = redis.get(f"file:content:{task_id}") if redis else None
    if not content_hex:
        TaskTracker.set_status(task_id, TaskStatus.FAILED, {"error": "文件内容已过期或丢失"})
        return
    # 注意：不能在这里 delete 文件内容——处理失败后 RabbitMQ 会重试，
    # 重试时还要重新读内容；提前删除会导致重试必然失败（内容已过期或丢失）。
    # 内容缓存的清理改到成功路径（见下方 COMPLETED 分支）。
    content = bytes.fromhex(content_hex)

    try:
        await _process_content(task_id, filename, content, user_id)
        if redis:
            # 处理成功后再清理文件内容缓存（失败重试时还需要）
            redis.delete(f"file:content:{task_id}")
            redis.setex(idempotent_key, 86400, "1")
    except Exception:
        logger.exception("文档处理失败 | task_id=%s", task_id)
        raise  # 让 RabbitMQ 重试机制接管
