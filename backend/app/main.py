import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.config import get_settings
from app.logging import setup_logging, get_trace_id
from app.middleware.logging import TraceMiddleware
from app.tasks.scheduler import scheduler_manager

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
    yield
    scheduler_manager.shutdown()
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求追踪中间件（在 CORS 之后，路由之前）
app.add_middleware(TraceMiddleware)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = get_trace_id()
    logger.bind(trace_id=trace_id).exception(
        f"未处理的异常: {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"服务器内部错误: {str(exc)}",
            "trace_id": trace_id,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
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
