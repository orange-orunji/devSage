import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.utils.SQL_database import SessionLocal
from app.schemas.user import (
    User, AuthResponse, ProfileResponse, ProfileUpdateRequest, PasswordChangeRequest,
)
from app.utils.auth import (
    generate_hash_password, verify_password, create_access_token, get_current_user,
)
from pydantic import BaseModel

import contextvars

logger = logging.getLogger("rag.auth")
router = APIRouter()
s = get_settings()

current_user_ctx : contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user",default="agent"
)

# 请求体格式：{"username": "xxx", "password": "xxx"}
class AutoRequest(BaseModel):
    username: str
    password: str

# 定义获取连接对象类,用database下的SessionLocal会话类来获取
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=AuthResponse)
def register(request : AutoRequest,db : Session = Depends(get_db)):
    # 密码长度校验（bcrypt 限制 72 字节）
    if len(request.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="密码过长，请使用不超过 72 字节的密码（约 24 个中文字符）")
    #去重
    first = db.query(User).filter(User.username == request.username).first()
    if first:
        raise  HTTPException(status_code=400,detail="用户已存在")
    # 注册相关用户信息
    user = User(username=request.username, hashed_password=generate_hash_password(request.password),
                role="user")
    db.add(user)
    db.commit()
    return {"message":"用户注册成功"}


@router.post("/login", response_model=AuthResponse)
def login(request : AutoRequest,db : Session = Depends(get_db)):
    target_user = db.query(User).filter(User.username == request.username).first()
    if not target_user or not verify_password(request.password,target_user.hashed_password):
        raise  HTTPException(status_code=400,detail="用户或密码错误")
    token = create_access_token(data={"sub": target_user.username, "user_id": target_user.id,
                                     "role": target_user.role or "user"})
    return {"access_token": token, "token_type": "bearer"}


# ── 用户资料 ──

_AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_AVATAR_MAX = 5 * 1024 * 1024  # 5MB（前端已自动压缩，此限制为回退上传兜底）


def _profile_dict(user: User) -> dict:
    return {
        "username": user.username,
        "display_name": user.display_name or "",
        "avatar": user.avatar or "",
        "bio": user.bio or "",
        "role": user.role or "user",
    }


def _get_db_user(db: Session, current_user: dict) -> User:
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/me", response_model=ProfileResponse)
def get_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户资料"""
    return _profile_dict(_get_db_user(db, current_user))


@router.put("/me", response_model=ProfileResponse)
def update_profile(request: ProfileUpdateRequest, current_user: dict = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """更新昵称与个性签名（登录名不可改）"""
    user = _get_db_user(db, current_user)
    user.display_name = request.display_name.strip()
    user.bio = request.bio.strip()
    db.commit()
    db.refresh(user)
    logger.info("资料更新 | user=%s | 昵称=%s", user.username, user.display_name)
    return _profile_dict(user)


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """上传头像（jpg/png/webp/gif，≤5MB），旧头像文件自动清理"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _AVATAR_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 jpg / png / webp / gif 图片")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > _AVATAR_MAX:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")

    user = _get_db_user(db, current_user)

    os.makedirs(s.AVATAR_DIR, exist_ok=True)
    # 清理旧头像文件
    if user.avatar:
        old_path = os.path.join(s.AVATAR_DIR, os.path.basename(user.avatar))
        if os.path.exists(old_path):
            os.remove(old_path)

    filename = f"{user.id}_{int(time.time())}{ext}"
    with open(os.path.join(s.AVATAR_DIR, filename), "wb") as f:
        f.write(content)
    user.avatar = f"/avatars/{filename}"
    db.commit()
    logger.info("头像更新 | user=%s | file=%s | %dKB", user.username, filename, len(content) // 1024)
    return {"avatar": user.avatar}


@router.post("/me/password")
def change_password(request: PasswordChangeRequest, current_user: dict = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """修改密码（需验证原密码）"""
    user = _get_db_user(db, current_user)
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if len(request.new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="密码过长，请使用不超过 72 字节的密码")
    user.hashed_password = generate_hash_password(request.new_password)
    db.commit()
    logger.info("密码修改 | user=%s", user.username)
    return {"message": "密码修改成功"}

