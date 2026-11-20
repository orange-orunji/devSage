import asyncio
import logging
import uuid

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.schemas.response import UnifiedResponse
from app.services.document import validate_upload
from app.services.vector_store import vector_store_service as vss
from app.utils.auth import get_current_user
from app.utils.rabbitmq import rabbitmq
from app.utils.redis_client import get_redis
from app.utils.task_handler import process_document_inline
from app.utils.task_status import TaskTracker, TaskStatus

logger = logging.getLogger("rag.upload")
router = APIRouter()


@router.post("/upload", summary="异步上传文件", description="支持 .txt, .docx, .pdf, .md 格式，自动去重、分割、向量化存储")
async def document_upload(file: UploadFile = File(..., description="待上传的文件"), current_user: dict = Depends(get_current_user)) -> UnifiedResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # ★ 仅做校验（大小、格式），不处理内容
    error = validate_upload(content, file.filename)
    if error:
        return error

    task_id = uuid.uuid4().hex

    # ★ 文件内容存入 Redis（600秒过期），消息体只传元数据
    redis = get_redis()
    if redis:
        redis.setex(f"file:content:{task_id}", 600, content.hex())

    TaskTracker.set_status(task_id, TaskStatus.PENDING, {"filename": file.filename})

    # ★ 优先走队列；队列不可用（未启动/断连）时降级为本进程同步处理，
    #   避免直接抛 500 导致上传功能整体失效（缺陷 D-01）。
    degraded = False
    try:
        await rabbitmq.publish("document.upload", {
            "task_id": task_id,
            "filename": file.filename,
            "user_id": current_user["user_id"],
        })
    except Exception as exc:
        degraded = True
        logger.warning("RabbitMQ 不可用，上传转为同步处理 | task_id=%s | err=%s", task_id, exc)
        asyncio.create_task(
            process_document_inline(task_id, file.filename, content, current_user["user_id"])
        )

    logger.info("接收上传 | task_id=%s | filename=%s | 大小=%dKB | user=%s | 队列=%s",
                task_id, file.filename, len(content) // 1024, current_user["user_id"],
                "降级" if degraded else "正常")

    return UnifiedResponse.success(
        code=202,
        data={"task_id": task_id, "degraded": degraded},
        message=(f"文件 {file.filename} 已接收，队列不可用，正在同步处理中"
                 if degraded else f"文件 {file.filename} 已接收，正在异步处理中")
    )

@router.get("/upload/status/{task_id}", summary="查询上传任务状态")
async def get_upload_status(task_id: str) -> UnifiedResponse:
    status = TaskTracker.get_status(task_id)
    if not status:
        return UnifiedResponse(code=404, message="任务不存在或已过期")
    return UnifiedResponse.success(data=status)


@router.get("/stats", summary="知识库概览统计", description="空状态概览卡数据源：文档数、分块数、最近文档")
async def knowledge_base_stats(current_user: dict = Depends(get_current_user)) -> UnifiedResponse:
    documents = vss.get_all_documents()

    # 按文件名（metadata.source）聚合分块数
    file_map: dict[str, dict] = {}
    for doc in documents:
        source = doc.metadata.get("source", "未知文件")
        if source not in file_map:
            file_map[source] = {
                "name": source,
                "chunks": 0,
                "create_time": doc.metadata.get("create_time", ""),
            }
        file_map[source]["chunks"] += 1

    files = sorted(file_map.values(), key=lambda x: str(x["create_time"]), reverse=True)
    return UnifiedResponse.success(data={
        "doc_count": len(files),
        "chunk_count": len(documents),
        "recent_files": [f["name"] for f in files[:3]],
    })