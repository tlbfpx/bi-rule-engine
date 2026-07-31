"""缓存工具 — 薄封装层，委托到 core/cache.py 的 RedisCache。

统一通过 ICache 协议提供缓存能力，避免多处直接操作 Redis 客户端。
保留模块级函数签名以兼容现有调用方。
"""
import json
from typing import Optional

from loguru import logger

from app.config import get_settings
from app.core.cache import RedisCache

settings = get_settings()

# 使用 core/cache.py 的 RedisCache 作为唯一缓存实现
_cache = RedisCache(redis_url=settings.REDIS_URL)


async def cache_get(key: str) -> Optional[dict]:
    """获取缓存值（JSON 反序列化）。"""
    return await _cache.get(key)


async def cache_set(key: str, value: dict, ttl: int = 600) -> None:
    """设置缓存值（JSON 序列化），默认 600 秒过期。"""
    await _cache.set(key, value, ttl=ttl)


async def cache_delete(pattern: str) -> None:
    """删除匹配 pattern 的缓存 key。

    使用 SCAN 迭代器而非 KEYS，避免在大数据量时阻塞 Redis。
    """
    deleted = 0
    async for key in _cache._redis.scan_iter(match=pattern, count=100):
        await _cache._redis.delete(key)
        deleted += 1
    if deleted:
        logger.debug(f"缓存清理: 删除 {deleted} 个 key (pattern={pattern})")


async def cache_exists(key: str) -> bool:
    """判断缓存键是否存在。"""
    return await _cache.exists(key)
