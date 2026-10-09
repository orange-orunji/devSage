from pathlib import Path
from typing import Tuple, Literal
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录（settings.py 位于 app/config/ 下，往上三层才是根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── 运行环境 ──
    ENV: Literal["dev", "staging", "production"] = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:8501", "http://127.0.0.1:8000", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """兼容 .env 中的逗号分隔字符串，自动拆分为列表"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── API 配置 ──
    SILICON_API_KEY: str
    SILICON_BASE_URL: str = "https://api.deepseek.com"
    SILICON_MODEL: str = "deepseek-flash"

    # —— 联网搜索（博查 Bocha，二期 web_search 用）——
    BOCHA_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""

    # ── Embedding 配置（DashScope OpenAI 兼容接口）──
    # text-embedding-v4 免费额度用完后转按量付费：0.5 元/百万 Token，项目全量用量不到 0.5 元
    # 注意：更换 EMBEDDING_MODEL 后必须全量重建知识库（python -m app.rebuild_kb）
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v4"

    # ── chroma 配置 ──
    CHROMA_DIR: str = str(BASE_DIR / "app/data/storage/chroma_db")
    CHROMA_NAME: str = "enterprise_knowledge"

    # ── md5 配置 ──
    MD5_PATH: str = str(BASE_DIR / "app/data/storage/md5_records.txt")

    # ── 文件上传 ──
    MAX_FILE_SIZE: int = 10
    ALLOWED_SUFFIXES: Tuple[str, ...] = (".txt", ".docx", ".pdf", ".md")
    UPLOAD_DIR: str = str(BASE_DIR / "data/uploads")

    # ── 文本切割 ──
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    SEPARATORS: list[str] = ["\n\n", "\n", "\t", " ", ".", ",", "!", "?", ";", "。", "，"]

    # ── 向量检索 ──
    VECTOR_MAX_NUM: int = 3

    # ── 聊天历史 ──
    CHAT_HISTORY_STORAGY_PATH: str = str(BASE_DIR / "app/data/chat_history")

    # ── redis 配置 ──
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: str = ""  # 无密码时留空即可
    REDIS_USER_PREFIX: str = "qa"
    REDIS_EXPIRE: int = 600

    # ── RabbitMQ 配置 ──
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "rag"
    RABBITMQ_PASSWORD: str = "123456"
    RABBITMQ_VHOST: str = "/rag"

    # ── 消息队列重试 ──
    MQ_MAX_RETRIES: int = 3
    MQ_RETRY_DELAY_SECONDS: int = 5

    # ── 数据库连接池 ──
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # ── 限流 ──
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CHAT_PER_MINUTE: str = "10/minute"

    # —— 下载路径 ——
    REPORT_FILE_PATH : str  = str(BASE_DIR / "app/data/report")
    AVATAR_DIR: str = str(BASE_DIR / "app/data/avatars")    # 用户头像存储目录（/avatars 静态挂载）

    # —— 邮箱路径 ——
    SMTP_HOST: str         # QQ邮箱 / 企业邮箱
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str     # QQ邮箱用授权码，不是登录密码

    # —— 检查点保存路径 ——
    CHECKPOINT_DIR: str = str(BASE_DIR / "app/data/checkpoints.db")

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

@lru_cache
def get_settings() -> settings:
    return settings()