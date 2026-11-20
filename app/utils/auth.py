import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta


# JWT 密钥优先从环境变量读取，未配置时回退到默认值（保证已有 Token 兼容）
SECRET_ID = os.getenv("JWT_SECRET", "my_secret_key_for_demo") # 加密前缀
ALGORITHM = "HS256" # 加密方式
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7 # JWT令牌存在时间
# 生成加密上下文文本对象
pwd_content = CryptContext(schemes=["pbkdf2_sha256"],deprecated="auto")

def generate_hash_password(password : str) -> str:
    """加密明文密码成指定的加密后的密码"""
    return pwd_content.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码和目标哈希值是否一样"""
    return pwd_content.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """生成JWT令牌方法"""
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, str(SECRET_ID), algorithm=ALGORITHM)


def decode_token(token : str) -> dict:
    """解析JWT令牌方法,拿到令牌中的用户信息"""
    return jwt.decode(token,SECRET_ID,algorithms=[ALGORITHM])

security = HTTPBearer()
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """注入管理状态验证方法"""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        return payload  # {"user_id": 1, "sub": "test", ...}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 Token")

def require_admin(payload: dict = Depends(get_current_user)) -> dict:
    """管理员依赖：令牌中 role 必须为 admin，否则 403。"""
    if (payload.get("role") or "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return payload
