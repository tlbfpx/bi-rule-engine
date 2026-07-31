"""API 层全局异常处理器。

将 BizException 和 FastAPI HTTPException 统一包装为 Result.fail 响应体，
保证错误响应格式与成功响应一致（success/code/message/data）。
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import BizException
from app.core.response import Result


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，异常响应统一为 Result 格式。"""

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        return JSONResponse(
            status_code=exc.code.http_status,
            content=Result.fail(
                code=exc.code.code,
                message=exc.detail or exc.code.message,
                data=exc.data,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=Result.fail(
                code="HTTP_ERROR",
                message=exc.detail,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """统一 Pydantic 校验错误的响应格式（默认 FastAPI 返回 {detail: [...]}）"""
        errors = exc.errors()
        # 取第一条错误的简要信息作为 message
        first_msg = errors[0]["msg"] if errors else "参数校验失败"
        loc = ".".join(str(l) for l in errors[0]["loc"][1:]) if errors else ""
        message = f"{loc}: {first_msg}" if loc else first_msg
        return JSONResponse(
            status_code=422,
            content=Result.fail(
                code="VALIDATION_ERROR",
                message=message,
                data=errors,
            ).model_dump(mode="json"),
        )
