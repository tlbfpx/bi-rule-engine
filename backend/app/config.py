import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "BI Rule Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development / staging / production
    CORS_ORIGINS: list[str] = ["*"]

    # 元数据库 (MySQL)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "bi_rule"
    DB_PASSWORD: str = "bi_rule_pass"
    DB_NAME: str = "bi_rule_engine"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}"
                f"@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # 加密
    ENCRYPTION_KEY: str = "change-me-32-bytes-key-here!!"

    @property
    def ENCRYPTION_KEY_BYTES(self) -> bytes:
        """确保加密密钥至少 32 字节，使用 SHA256 派生避免弱密钥"""
        import hashlib
        key = self.ENCRYPTION_KEY.encode("utf-8")
        if len(key) < 32:
            return hashlib.sha256(key).digest()
        return key[:32]

    # 文件存储
    STORAGE_DIR: str = "/workspace/bi-rule-engine/storage"
    MAX_UPLOAD_SIZE_MB: int = 100

    # MySQL 数据源限制
    MAX_QUERY_ROWS: int = 2000000
    QUERY_TIMEOUT_SECONDS: int = 600

    # 调度器
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"
    SCHEDULER_MAX_INSTANCES: int = 3
    SCHEDULER_COALESCE: bool = True  # 错过任务合并执行
    ETL_DEFAULT_TIMEOUT_SECONDS: int = 3600
    ETL_BATCH_SIZE: int = 10000

    # ── 日志 ──
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/tmp/bi-rule-engine"

    # 日志轮转策略
    LOG_ACCESS_ROTATION: str = "30 MB"
    LOG_ACCESS_RETENTION: str = "14 days"
    LOG_ERROR_ROTATION: str = "10 MB"
    LOG_ERROR_RETENTION: str = "30 days"
    LOG_APP_ROTATION: str = "30 MB"
    LOG_APP_RETENTION: str = "14 days"

    # 前端错误上报开关
    FRONTEND_ERROR_LOG_ENABLED: bool = True

    # 审计日志（默认关闭，按需开启）
    AUDIT_LOG_ENABLED: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        os.makedirs(self.LOG_DIR, exist_ok=True)
        # 生产环境防护：拒绝使用默认加密密钥（否则数据源密码等用公开值加密，形同明文）
        if self.ENVIRONMENT == "production" and self.ENCRYPTION_KEY == "change-me-32-bytes-key-here!!":
            raise RuntimeError(
                "生产环境必须设置 ENCRYPTION_KEY 环境变量（当前为默认值）"
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
