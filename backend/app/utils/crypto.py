import base64
import os
import hashlib
from loguru import logger
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import get_settings

settings = get_settings()


def _get_key() -> bytes:
    """[已废弃] 使用 \x00 填充的旧密钥 — 仅为解密历史数据保留，不再用于加密。"""
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    if len(key) < 32:
        return key.ljust(32, b"\x00")
    return key[:32]


def _get_new_key() -> bytes:
    """使用 SHA256 派生密钥（安全，生产推荐）"""
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    return hashlib.sha256(key).digest()


def encrypt(plaintext: str) -> str:
    """加密（使用 SHA256 派生密钥）"""
    aesgcm = AESGCM(_get_new_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"aes256gcm:{base64.b64encode(nonce + ciphertext).decode()}"


def decrypt(token: str) -> str:
    """解密：优先用 SHA256 派生密钥，失败时回退到旧密钥（兼容历史数据并告警）"""
    if not token.startswith("aes256gcm:"):
        raise ValueError("Invalid token format")
    data = base64.b64decode(token[10:])
    nonce, ciphertext = data[:12], data[12:]

    # 优先尝试新密钥（SHA256）
    try:
        aesgcm = AESGCM(_get_new_key())
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as e:
        logger.debug(f"SHA256 密钥解密失败，尝试旧密钥回退: {type(e).__name__}")

    # 兼容旧密钥（\x00 填充）— 仅解密用，并发出安全告警提示迁移
    logger.warning(
        "使用旧版 \\x00 填充密钥解密数据，建议通过重新保存触发加密迁移到 SHA256 派生密钥"
    )
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
