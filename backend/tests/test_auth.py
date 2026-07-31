"""认证模块单元测试 — JWT + bcrypt"""
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hash_and_verify():
    """密码哈希与校验"""
    h = hash_password("secret123")
    assert h != "secret123"
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_password_truncation():
    """超过 72 字节的密码自动截断（bcrypt 限制）"""
    long_pwd = "a" * 100
    h = hash_password(long_pwd)
    # 前 72 字节相同 → 验证通过
    assert verify_password(long_pwd, h)
    # 前 72 字节相同的不同字符串 → 同样通过（bcrypt 设计限制）
    assert verify_password("a" * 72 + "different_tail", h)


def test_jwt_create_and_decode():
    """JWT 签发与验证"""
    payload = {"sub": "user-uuid-123", "username": "admin", "role": "admin"}
    token = create_access_token(payload)
    assert token is not None
    assert len(token) > 50

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["username"] == "admin"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_jwt_invalid_token():
    """无效 JWT 返回 None"""
    assert decode_access_token("invalid.token.here") is None
    assert decode_access_token("") is None


def test_jwt_expired():
    """过期 JWT 返回 None"""
    from datetime import timedelta
    # 创建一个已经过期的 token
    token = create_access_token(
        {"sub": "user-1"},
        expires_delta=timedelta(seconds=-1),
    )
    assert decode_access_token(token) is None
