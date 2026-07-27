"""前端错误上报接口"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from loguru import logger

from app.logging import set_trace_id, generate_trace_id, get_trace_id

router = APIRouter(prefix="/logs", tags=["日志上报"])


class FrontendErrorPayload(BaseModel):
    """前端错误上报请求体"""
    message: str = Field(..., description="错误消息")
    stack: str | None = Field(None, description="错误堆栈")
    url: str | None = Field(None, description="出错页面 URL")
    user_agent: str | None = Field(None, description="浏览器 UA")
    trace_id: str | None = Field(None, description="前端缓存的 trace_id")
    timestamp: str | None = Field(None, description="错误发生时间")


@router.post("/frontend-error", status_code=204)
async def report_frontend_error(request: Request, body: FrontendErrorPayload):
    """
    接收前端上报的错误日志。

    - 关联前端缓存的 trace_id（如有）
    - 记录到 error.log
    - 返回 204 No Content 避免前端额外处理
    """
    # 优先使用前端传来的 trace_id，否则使用当前上下文或生成新的
    effective_trace_id = body.trace_id or get_trace_id() or generate_trace_id()

    # 截断堆栈避免日志过大
    stack_snippet = (body.stack or "")[:1000]

    logger.bind(trace_id=effective_trace_id).error(
        "[FRONTEND] {} | url={} | ua={} | stack={}",
        body.message,
        body.url or "unknown",
        (body.user_agent or "unknown")[:200],
        stack_snippet,
    )
