import json
from typing import Optional
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def cache_get(key: str) -> Optional[dict]:
    data = await redis_client.get(key)
    return json.loads(data) if data else None


async def cache_set(key: str, value: dict, ttl: int = 600) -> None:
    await redis_client.set(key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(pattern: str) -> None:
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)


async def cache_exists(key: str) -> bool:
    return await redis_client.exists(key) > 0
