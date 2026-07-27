import base64
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import get_settings

settings = get_settings()


def _get_key() -> bytes:
    """获取加密密钥（向后兼容：短密钥用 \x00 填充到 32 字节）"""
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    if len(key) < 32:
        return key.ljust(32, b"\x00")
    return key[:32]


def _get_new_key() -> bytes:
    """使用 SHA256 派生新密钥（生产推荐）"""
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    return hashlib.sha256(key).digest()


def encrypt(plaintext: str) -> str:
    """加密（使用 SHA256 派生密钥）"""
    aesgcm = AESGCM(_get_new_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"aes256gcm:{base64.b64encode(nonce + ciphertext).decode()}"


def decrypt(token: str) -> str:
    """解密：先尝试新密钥(SHA256)，失败则用旧密钥(\x00填充)兼容历史数据"""
    if not token.startswith("aes256gcm:"):
        raise ValueError("Invalid token format")
    data = base64.b64decode(token[10:])
    nonce, ciphertext = data[:12], data[12:]

    # 先尝试新密钥
    try:
        aesgcm = AESGCM(_get_new_key())
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        pass

    # 兼容旧密钥（\x00 填充）
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
