"""
请求追踪中间件

功能：
1. 从 X-Trace-Id Header 提取或生成 trace_id
2. 记录每个 API 请求的方法、路径、状态码、耗时、客户端 IP
3. 响应时注入 X-Trace-Id Header 供前端缓存
4. 性能目标：额外开销 < 0.5ms
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging import set_trace_id, generate_trace_id, get_trace_id
from loguru import logger


class TraceMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件 — 为每个 HTTP 请求绑定 trace_id"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. 提取或生成 trace_id
        trace_id = request.headers.get("X-Trace-Id") or generate_trace_id()
        set_trace_id(trace_id)

        # 2. 记录请求开始时间
        start_time = time.perf_counter()

        # 3. 执行请求
        response = await call_next(request)

        # 4. 计算耗时
        duration_ms = (time.perf_counter() - start_time) * 1000

        # 5. 记录访问日志（JSON 结构化，路由到 access.log）
        client_ip = request.client.host if request.client else "unknown"
        logger.bind(log_type="access").info(
            "{} {} {} {:.2f}ms ip={}",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
        )

        # 6. 注入 trace_id 到响应头
        response.headers["X-Trace-Id"] = trace_id

        return response
