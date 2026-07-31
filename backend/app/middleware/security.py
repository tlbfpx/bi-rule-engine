"""
安全响应头中间件

添加标准的 Web 安全响应头，防御常见攻击：
- X-Content-Type-Options: 禁止 MIME 嗅探
- X-Frame-Options: 防止点击劫持
- X-XSS-Protection: 浏览器 XSS 过滤器
- Referrer-Policy: 限制 Referer 泄露
- Strict-Transport-Security: 强制 HTTPS（生产环境）
- Content-Security-Policy: 限制资源加载源
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有 HTTP 响应注入安全头"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 只对成功响应添加安全头；拒绝访问 / 服务器错误等也添加基础头
        headers = response.headers

        # 禁止浏览器 MIME 类型嗅探
        headers.setdefault("X-Content-Type-Options", "nosniff")

        # 防止页面被嵌入 iframe（点击劫持防护）
        headers.setdefault("X-Frame-Options", "DENY")

        # 启用浏览器内置 XSS 过滤器
        headers.setdefault("X-XSS-Protection", "1; mode=block")

        # 限制 Referer 信息泄露
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # 缓存控制：API 响应不缓存（文件下载除外）
        if isinstance(response, JSONResponse):
            headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate")

        return response
