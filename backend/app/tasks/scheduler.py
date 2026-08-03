"""APScheduler 调度器封装"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import select
from loguru import logger

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.logging import generate_trace_id, set_trace_id
from app.models.etl_job import ETLJob
from app.engine.etl_runner import run_etl_job

settings = get_settings()

JOB_ID_PREFIX = "etl_job_"


def _job_id(etl_job_id: str) -> str:
    return f"{JOB_ID_PREFIX}{etl_job_id}"


def _parse_cron(cron_expression: str) -> dict:
    """把 5 字段 cron 解析为 CronTrigger 参数"""
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"cron 表达式需要 5 个字段，实际 {len(parts)}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


class SchedulerManager:
    """调度器管理器"""

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None

    @property
    def scheduler(self) -> AsyncIOScheduler:
        if self._scheduler is None:
            raise RuntimeError("调度器尚未初始化")
        return self._scheduler

    def initialize(self, event_loop=None):
        """初始化 AsyncIOScheduler — 使用 DB jobstore 实现重启恢复"""
        if self._scheduler is not None:
            return
        # 使用 SQLAlchemyJobStore 持久化调度状态到 MySQL
        jobstore = SQLAlchemyJobStore(
            url=settings.DATABASE_URL_SYNC,
            tablename="apscheduler_jobs",
        )
        kwargs = dict(
            timezone=settings.SCHEDULER_TIMEZONE,
            jobstores={"default": jobstore},
            job_defaults={
                "coalesce": settings.SCHEDULER_COALESCE,
                "max_instances": settings.SCHEDULER_MAX_INSTANCES,
                "misfire_grace_time": 3600,
            },
        )
        if event_loop:
            kwargs["event_loop"] = event_loop
        self._scheduler = AsyncIOScheduler(**kwargs)
        logger.info("调度器已初始化（DB jobstore）")

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("调度器已启动")

    def shutdown(self, wait: bool = True):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("调度器已关闭")

    async def load_jobs(self):
        """从数据库加载所有启用的 ETL 任务"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ETLJob).where(ETLJob.enabled == True))
            jobs = result.scalars().all()
            for job in jobs:
                try:
                    self.add_job_sync(job)
                except Exception as e:
                    logger.error(f"加载 ETL 任务到调度器失败 [job={job.id}]: {e}")
        logger.info(f"已加载 {len(jobs)} 个调度任务")

    def add_job_sync(self, job: ETLJob):
        """同步方式向调度器添加任务"""
        job_id = _job_id(job.id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        cron_kwargs = _parse_cron(job.cron_expression)
        trigger = CronTrigger(
            **cron_kwargs,
            timezone=job.timezone or settings.SCHEDULER_TIMEZONE,
        )
        self._scheduler.add_job(
            func=self._run_etl_job_wrapper,
            trigger=trigger,
            id=job_id,
            name=job.job_name,
            args=[job.id],
            replace_existing=True,
        )
        logger.info(f"已注册调度任务: {job.job_name} ({job.cron_expression})")

    async def add_job(self, job: ETLJob):
        """异步包装"""
        await asyncio.to_thread(self.add_job_sync, job)

    async def remove_job(self, job_id: str):
        """移除调度任务"""
        def _remove():
            full_id = _job_id(job_id)
            if self._scheduler.get_job(full_id):
                self._scheduler.remove_job(full_id)
                logger.info(f"已移除调度任务: {job_id}")
        await asyncio.to_thread(_remove)

    async def reschedule_job(self, job: ETLJob):
        """重新调度任务"""
        if not job.enabled:
            await self.remove_job(job.id)
            return
        await self.add_job(job)

    async def _run_etl_job_wrapper(self, job_id: str):
        """调度器触发时调用 — 生成独立 trace_id 与用户请求隔离"""
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        logger.info(f"调度器触发 ETL 任务: {job_id}")
        try:
            await run_etl_job(job_id, trace_id=trace_id)
        except Exception as e:
            logger.exception(f"调度器执行 ETL 任务失败 [job={job_id}]: {e}")


scheduler_manager = SchedulerManager()
