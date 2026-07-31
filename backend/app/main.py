import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.config import get_settings
from app.logging import setup_logging, get_trace_id
from app.middleware.logging import TraceMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.tasks.scheduler import scheduler_manager
from app.api.v1.exceptions import register_exception_handlers
from app.core.response import Result

settings = get_settings()

# 初始化日志系统
setup_logging(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    loop = asyncio.get_running_loop()
    scheduler_manager.initialize(event_loop=loop)
    scheduler_manager.start()
    await scheduler_manager.load_jobs()

    # ── 自动创建默认管理员（首次启动） ──
    try:
        from sqlalchemy import select
        from app.db import AsyncSessionLocal
        from app.models.user import User
        from app.core.security import hash_password
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
            )
            if not result.scalar_one_or_none():
                admin = User(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                    role="admin",
                    enabled=True,
                    display_name="系统管理员",
                )
                session.add(admin)
                await session.commit()
                logger.info("默认管理员账号已创建")
    except Exception as e:
        logger.warning(f"创建默认管理员失败（可能 users 表尚未创建）: {e}")

    yield
    # ── 优雅关闭：按依赖顺序释放资源 ──
    # 1. 先停止调度器（不再派发新任务）
    scheduler_manager.shutdown(wait=False)
    # 2. 关闭所有 WebSocket 连接
    from app.api.v1.ws import manager as ws_manager
    for task_id, conns in list(ws_manager.active_connections.items()):
        for ws in list(conns):
            try:
                await ws.close(code=1001, reason="服务器关闭")
            except Exception:
                pass
        ws_manager.active_connections.clear()
    # 3. 关闭 Redis 连接池
    from app.cache import _cache
    try:
        await _cache.close()
    except Exception as e:
        logger.warning(f"关闭 Redis 连接失败: {e}")
    # 4. 释放数据库连接池
    from app.db import engine as db_engine
    try:
        await db_engine.dispose()
    except Exception as e:
        logger.warning(f"释放数据库引擎失败: {e}")
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 统一异常处理：BizException / HTTPException → Result.fail 响应体
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求追踪中间件（在 CORS 之后，路由之前）
app.add_middleware(TraceMiddleware)

# 安全响应头中间件（在所有中间件之后，确保 headers 最终写入）
app.add_middleware(SecurityHeadersMiddleware)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = get_trace_id()
    logger.bind(trace_id=trace_id).exception(
        f"未处理的异常: {request.method} {request.url.path}"
    )
    # 生产环境不向客户端泄露内部异常细节（SQL/路径/库内部信息），仅返回通用提示 + trace_id
    message = (
        "服务器内部错误"
        if settings.ENVIRONMENT == "production"
        else f"服务器内部错误: {exc}"
    )
    return JSONResponse(
        status_code=500,
        content=Result.fail(code="INTERNAL_ERROR", message=message).model_dump(mode="json") | {"trace_id": trace_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=Result.fail(code="BUSINESS_ERROR", message=str(exc)).model_dump(mode="json"),
    )


from app.api.v1.router import api_router
from app.api.v1.ws import router as ws_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/ws")


@app.get("/api/health")
async def health_check():
    """健康检查 - 验证数据库连接"""
    db_ok = True
    db_error = None
    try:
        from sqlalchemy import text
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        db_error = str(e)

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": {"ok": db_ok, "error": db_error},
    }
