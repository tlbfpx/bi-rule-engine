"""缓存抽象 — 通过接口隔离缓存实现（阿里规约）。

定义 ICache 协议统一缓存接口，提供两种实现：
- MemoryCache: 基于内存字典的缓存，开发环境使用
- RedisCache: 基于 Redis 的缓存，生产环境使用

通过接口隔离，上层代码依赖 ICache 协议而非具体实现，
可按环境切换缓存策略。
"""
import json
import time
from typing import Any, Protocol, runtime_checkable

import redis.asyncio as aioredis


@runtime_checkable
class ICache(Protocol):
    """缓存接口协议。

    所有缓存实现需遵循此接口，方法均为异步。
    """

    async def get(self, key: str) -> Any | None:
        """获取缓存值。"""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值，ttl 为过期秒数。"""
        ...

    async def delete(self, key: str) -> None:
        """删除缓存值。"""
        ...

    async def exists(self, key: str) -> bool:
        """判断缓存键是否存在。"""
        ...


class MemoryCache:
    """内存缓存实现（基于 dict + 时间戳，开发环境用）。

    使用 time.monotonic 计算 TTL，不受系统时钟调整影响。
    不支持跨进程共享，仅适用于单实例开发环境。
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        """获取缓存值，过期则返回 None 并清理。"""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if expire_at is not None and time.monotonic() > expire_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期秒数，None 表示永不过期
        """
        expire_at = time.monotonic() + ttl if ttl is not None else None
        self._store[key] = (value, expire_at)

    async def delete(self, key: str) -> None:
        """删除缓存值，键不存在时静默忽略。"""
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        """判断缓存键是否存在且未过期。"""
        entry = self._store.get(key)
        if entry is None:
            return False
        _, expire_at = entry
        if expire_at is not None and time.monotonic() > expire_at:
            del self._store[key]
            return False
        return True

    async def close(self) -> None:
        """关闭缓存（内存缓存无需操作）。"""
        pass


class RedisCache:
    """Redis 缓存实现（生产环境）。

    通过 redis.asyncio 异步客户端连接 Redis，
    值以 JSON 序列化存储，支持 TTL 过期。

    Args:
        redis_url: Redis 连接 URL（如 redis://localhost:6379/0）
    """

    def __init__(self, redis_url: str) -> None:
        self._redis = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )

    async def get(self, key: str) -> Any | None:
        """获取缓存值，JSON 反序列化。"""
        data = await self._redis.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值，JSON 序列化。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期秒数，None 表示永不过期
        """
        serialized = json.dumps(value, default=str)
        if ttl is not None:
            await self._redis.set(key, serialized, ex=ttl)
        else:
            await self._redis.set(key, serialized)

    async def delete(self, key: str) -> None:
        """删除缓存值。"""
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """判断缓存键是否存在。"""
        return await self._redis.exists(key) > 0

    async def close(self) -> None:
        """关闭 Redis 连接池（优雅关闭时调用）。"""
        await self._redis.aclose()
