"""认证相关 Pydantic 模型"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
    role: str
    display_name: str | None = None


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    display_name: str | None = None
    enabled: bool
