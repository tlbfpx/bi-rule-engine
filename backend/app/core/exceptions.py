"""统一异常体系 — 错误码与错误信息分离（阿里规约）。

所有业务异常继承 BizException，携带 BizErrorCode 枚举，
实现 HTTP 状态码、业务状态码、错误信息三者分离。
"""
from enum import Enum
from typing import Any


class BizErrorCode(Enum):
    """业务错误码枚举。

    每个成员值为 (http_status, code, message) 三元组：
    - http_status: HTTP 状态码
    - code: 业务状态码（字符串，供前端区分错误类型）
    - message: 默认错误提示信息
    """

    NOT_FOUND = (404, "RESOURCE_NOT_FOUND", "资源不存在")
    DUPLICATE = (409, "RESOURCE_DUPLICATE", "资源重复")
    VALIDATION_ERROR = (422, "VALIDATION_ERROR", "参数校验失败")
    BUSINESS_ERROR = (400, "BUSINESS_ERROR", "业务异常")
    INTERNAL_ERROR = (500, "INTERNAL_ERROR", "服务器内部错误")
    DEPENDENCY_ERROR = (503, "DEPENDENCY_ERROR", "依赖服务异常")

    def __init__(self, http_status: int, code: str, message: str) -> None:
        self.http_status = http_status
        self.code = code
        self.message = message


class BizException(Exception):  # noqa: N818 - 规约要求命名为 BizException
    """业务异常基类。

    Attributes:
        code: 业务错误码枚举
        detail: 异常详细信息（覆盖默认 message）
        data: 附加数据（可选，如校验错误字段列表）
    """

    def __init__(
        self,
        code: BizErrorCode = BizErrorCode.BUSINESS_ERROR,
        detail: str | None = None,
        data: Any = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.data = data
        super().__init__(detail or code.message)

    def __str__(self) -> str:
        """返回格式化错误信息：[业务状态码] 详细信息。"""
        msg = self.detail or self.code.message
        return f"[{self.code.code}] {msg}"


class NotFoundException(BizException):
    """资源不存在异常，默认 code=NOT_FOUND。"""

    def __init__(self, detail: str | None = None, data: Any = None) -> None:
        super().__init__(code=BizErrorCode.NOT_FOUND, detail=detail, data=data)


class DuplicateException(BizException):
    """资源重复异常，默认 code=DUPLICATE。"""

    def __init__(self, detail: str | None = None, data: Any = None) -> None:
        super().__init__(code=BizErrorCode.DUPLICATE, detail=detail, data=data)


class ValidationException(BizException):
    """参数校验失败异常，默认 code=VALIDATION_ERROR。"""

    def __init__(self, detail: str | None = None, data: Any = None) -> None:
        super().__init__(code=BizErrorCode.VALIDATION_ERROR, detail=detail, data=data)
