"""安全工具 — 密码哈希 + JWT 签发/验证"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt, JWTError

from app.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    """生成 bcrypt 哈希"""
    # bcrypt 限制 72 字节，截断超长密码
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码"""
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))


def create_access_token(
    subject: str | dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """签发 JWT access token

    Args:
        subject: 可以是 user_id 字符串，也可以是包含更多 claims 的 dict
        expires_delta: 自定义过期时间，默认使用配置
    """
    if isinstance(subject, str):
        payload: dict[str, Any] = {"sub": subject}
    else:
        payload = dict(subject)

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """验证 JWT 并返回 payload，失败返回 None"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
