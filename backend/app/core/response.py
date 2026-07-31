"""统一响应体 — Result<T> 统一返回（阿里规约）。

所有 API 响应统一使用 Result 包装，包含成功标志、业务状态码、
提示信息、数据体、链路追踪 ID 和时间戳。
"""
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.exceptions import BizErrorCode

T = TypeVar("T")


class PageData(BaseModel, Generic[T]):
    """分页数据封装。

    Attributes:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码（从 1 开始）
        page_size: 每页条数
    """

    items: list[T]
    total: int
    page: int
    page_size: int


class Result(BaseModel, Generic[T]):
    """统一响应体。

    Attributes:
        success: 是否成功
        code: 业务状态码（"SUCCESS" 或 BizErrorCode.code）
        message: 提示信息
        data: 响应数据
        trace_id: 链路追踪 ID
        timestamp: 响应时间戳（自动生成）
    """

    success: bool
    code: str
    message: str
    data: T | None = None
    trace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def ok(cls, data: Any = None, message: str = "操作成功") -> "Result[Any]":
        """构建成功响应。

        Args:
            data: 响应数据
            message: 提示信息

        Returns:
            成功的 Result 实例
        """
        return cls(
            success=True,
            code="SUCCESS",
            message=message,
            data=data,
        )

    @classmethod
    def fail(
        cls,
        code: str | BizErrorCode,
        message: str,
        data: Any = None,
    ) -> "Result[None]":
        """构建失败响应。

        Args:
            code: 业务状态码（字符串或 BizErrorCode 枚举）
            message: 错误提示信息
            data: 附加数据（如校验错误详情）

        Returns:
            失败的 Result 实例
        """
        if isinstance(code, BizErrorCode):
            code_str = code.code
            msg = message or code.message
        else:
            code_str = code
            msg = message
        return cls(
            success=False,
            code=code_str,
            message=msg,
            data=data,
        )

    @classmethod
    def page(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "Result[PageData[Any]]":
        """构建分页成功响应。

        Args:
            items: 当前页数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页条数

        Returns:
            包含 PageData 的成功 Result 实例
        """
        page_data = PageData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
        return cls(
            success=True,
            code="SUCCESS",
            message="操作成功",
            data=page_data,
        )
