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

import json


async def _reaper_loop():
    """Reaper 协程 — 定期扫描心跳超时的 running 任务并标记为 failed。

    防止进程崩溃或 commit 失败导致 run_record 永久卡在 running。
    """
    from sqlalchemy import text, select
    from app.db import AsyncSessionLocal
    interval = settings.REAPER_INTERVAL_SECONDS
    timeout = settings.ETL_HEARTBEAT_TIMEOUT_SECONDS
    logger.info(f"Reaper 协程已启动 (扫描间隔={interval}s, 心跳超时={timeout}s)")

    while True:
        try:
            await asyncio.sleep(interval)
            async with AsyncSessionLocal() as session:
                # 查找 running 状态且心跳超过 timeout 的记录
                result = await session.execute(
                    text(
                        "SELECT id, etl_job_id, trace_id FROM etl_job_runs "
                        "WHERE status = 'running' "
                        "AND heartbeat_at IS NOT NULL "
                        "AND heartbeat_at < DATE_SUB(NOW(), INTERVAL :timeout SECOND)"
                    ),
                    {"timeout": timeout},
                )
                stale_runs = result.fetchall()
                if stale_runs:
                    for row in stale_runs:
                        run_id = row[0]
                        job_id = row[1]
                        logger.warning(
                            f"Reaper: 发现卡死任务 [run={run_id}, job={job_id}]，标记为 failed"
                        )
                        await session.execute(
                            text(
                                "UPDATE etl_job_runs SET status='failed', "
                                "completed_at=NOW(), "
                                "error_log=:err "
                                "WHERE id=:rid"
                            ),
                            {"rid": run_id, "err": json.dumps({
                                "message": f"任务心跳超时（超过 {timeout} 秒无响应），被 Reaper 标记为失败",
                                "exception": "HeartbeatTimeout",
                            })},
                        )
                    await session.commit()
                    logger.info(f"Reaper: 清理了 {len(stale_runs)} 个卡死任务")
        except asyncio.CancelledError:
            logger.info("Reaper 协程已停止")
            raise
        except Exception as e:
            logger.error(f"Reaper 扫描异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    loop = asyncio.get_running_loop()
    scheduler_manager.initialize(event_loop=loop)
    scheduler_manager.start()
    await scheduler_manager.load_jobs()

    # 注册 ETL 进度事件 → WebSocket 转发监听器
    from app.api.v1.ws import init_progress_listener
    init_progress_listener(loop)

    # 启动 Reaper 协程 — 定期扫描卡死的 running 任务
    reaper_task = asyncio.create_task(_reaper_loop())

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
    # 0. 停止 Reaper 协程
    reaper_task.cancel()
    try:
        await reaper_task
    except asyncio.CancelledError:
        pass
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
    # 4. 释放 ETL 数据源连接池缓存
    from app.engine.etl_runner import dispose_all_source_engines
    try:
        dispose_all_source_engines()
    except Exception as e:
        logger.warning(f"释放数据源连接池失败: {e}")
    # 5. 释放数据库连接池
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
