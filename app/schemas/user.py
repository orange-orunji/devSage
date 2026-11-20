from sqlalchemy import String,Column,Integer
from pydantic import BaseModel, Field
from app.utils.SQL_database import Base

# ── ORM 模型 ──

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    hashed_password = Column(String)

    # ── 资料字段（2026-09-13 新增，SQLite 迁移见 main.py lifespan）──
    display_name = Column(String, default="")   # 昵称（显示用，独立于登录名）
    avatar = Column(String, default="")         # 头像 URL（/avatars/filename.png）
    bio = Column(String, default="")            # 个性签名
    # ── 角色（2026-11-20 新增）：user 普通用户 / admin 管理员 ──
    role = Column(String, default="user")

# ── Pydantic 响应模型 ──

class AuthResponse(BaseModel):
    """登录/注册响应"""
    message: str = ""
    access_token: str | None = None
    token_type: str | None = None


class ProfileResponse(BaseModel):
    """用户资料"""
    username: str
    display_name: str = ""
    avatar: str = ""
    bio: str = ""
    role: str = "user"


class ProfileUpdateRequest(BaseModel):
    """更新昵称与个性签名"""
    display_name: str = Field("", max_length=30, description="昵称（显示名）")
    bio: str = Field("", max_length=100, description="个性签名")


class PasswordChangeRequest(BaseModel):
    """修改密码"""
    old_password: str
    new_password: str
