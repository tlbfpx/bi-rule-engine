"""通用响应模型：分页等。"""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """标准分页响应：{items, total, page, page_size}。"""
    items: list[T]
    total: int
    page: int
    page_size: int


class ItemsResponse(BaseModel, Generic[T]):
    """仅 items 的响应（如 /all 端点）。"""
    items: list[T]
