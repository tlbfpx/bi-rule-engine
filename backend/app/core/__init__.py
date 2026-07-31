"""核心基础设施模块 — 公共 API 导出。

统一导出异常体系、响应体、常量枚举、仓储模式、服务基类、
依赖注入容器和缓存抽象，供业务层按需引用。
"""
from app.core.cache import ICache, MemoryCache, RedisCache
from app.core.constants import (
    ETLJobStatus,
    ExtractMode,
    RuleType,
    TaskStatus,
    WriteMode,
)
from app.core.di import DIContainer
from app.core.exceptions import (
    BizErrorCode,
    BizException,
    DuplicateException,
    NotFoundException,
    ValidationException,
)
from app.core.repository import BaseRepository, IRepository
from app.core.response import PageData, Result
from app.core.service import BaseService

__all__ = [
    "BaseRepository",
    "BaseService",
    "BizErrorCode",
    "BizException",
    "DIContainer",
    "DuplicateException",
    "ETLJobStatus",
    "ExtractMode",
    "ICache",
    "IRepository",
    "MemoryCache",
    "NotFoundException",
    "PageData",
    "RedisCache",
    "Result",
    "RuleType",
    "TaskStatus",
    "ValidationException",
    "WriteMode",
]
