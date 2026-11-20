"""知识库管理接口：文档列表、删除、指标概览。"""
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.utils.auth import get_current_user, require_admin
from app.config.settings import get_settings
from app.schemas.response import UnifiedResponse
from app.services.bm25_service import bm25_service
from app.services.KnowledgeBase_md5_service import delete_md5
from app.services.vector_store import vector_store_service

logger = logging.getLogger("rag.kb")
router = APIRouter()


class DeleteRequest(BaseModel):
    name: str


def _group_docs():
    """按来源文件聚合切片，返回 (列表, 切片总数)。"""
    docs = vector_store_service.get_all_documents()
    agg = defaultdict(lambda: {"name": "", "chunks": 0, "create_time": ""})
    for d in docs:
        src = d.metadata.get("source", "未知文件")
        item = agg[src]
        item["name"] = src
        item["chunks"] += 1
        t = d.metadata.get("create_time", "")
        if t and str(t) > str(item["create_time"]):
            item["create_time"] = t
    files = sorted(agg.values(), key=lambda x: str(x["create_time"]), reverse=True)
    return files, len(docs)


@router.get("/documents", summary="文档列表")
async def list_documents(current_user: dict = Depends(get_current_user)) -> UnifiedResponse:
    files, chunk_total = _group_docs()
    return UnifiedResponse.success(data={
        "total": len(files),
        "chunk_total": chunk_total,
        "items": files,
    })


@router.post("/delete", summary="删除文档及其切片")
async def delete_document(body: DeleteRequest, current_user: dict = Depends(require_admin)) -> UnifiedResponse:
    name = (body.name or "").strip()
    if not name:
        return UnifiedResponse.error(code=400, message="文件名不能为空")
    s = get_settings()
    result = vector_store_service.chroma.get(where={"source": name})
    if not result["ids"]:
        return UnifiedResponse.error(code=404, message=f"文件不存在：{name}")
    removed = len(result["ids"])
    md5s = {m.get("md5") for m in result["metadatas"] if m.get("md5")}
    vector_store_service.chroma.delete(where={"source": name})
    for m in md5s:
        try:
            delete_md5(s.MD5_PATH, m)
        except Exception:
            logger.warning("清理 MD5 失败 | md5=%s", m)
    bm25_service.build_index(vector_store_service.get_all_documents())
    files, chunk_total = _group_docs()
    logger.info("删除文档 | name=%s | 切片=%d | 操作人=%s", name, removed, current_user.get("username"))
    return UnifiedResponse.success(data={
        "removed_chunks": removed,
        "total": len(files),
        "chunk_total": chunk_total,
    }, message=f"已删除 {name}（{removed} 个切片）")


@router.get("/metrics", summary="运行指标概览")
async def metrics(current_user: dict = Depends(get_current_user)) -> UnifiedResponse:
    s = get_settings()
    files, chunk_total = _group_docs()

    sessions = 0
    messages = 0
    assistant = 0
    per_day = defaultdict(int)
    today = datetime.now().date()
    week = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    for day in week:
        per_day[day] = 0

    base = os.path.join(os.path.dirname(os.path.dirname(s.CHROMA_DIR)), "chat_history")
    for root, _, names in os.walk(base):
        for n in names:
            if not n.endswith(".json") or n.startswith("_meta"):
                continue
            fp = os.path.join(root, n)
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            sessions += 1
            messages += len(data)
            assistant += sum(1 for m in data if m.get("type") in ("ai", "AIMessage"))
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).date().isoformat()
            if mtime in per_day:
                per_day[mtime] += 1

    size_mb = 0.0
    if os.path.isdir(s.CHROMA_DIR):
        size_mb = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(s.CHROMA_DIR) for f in fs) / 1024 / 1024

    return UnifiedResponse.success(data={
        "doc_count": len(files),
        "chunk_count": chunk_total,
        "session_count": sessions,
        "message_count": messages,
        "assistant_count": assistant,
        "vector_size_mb": round(size_mb, 2),
        "activity": [{"date": d, "sessions": per_day[d]} for d in week],
    })
