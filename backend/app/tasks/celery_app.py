"""异步任务 — Celery 配置与导出任务"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "bi_rule_engine",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.QUERY_TIMEOUT_SECONDS,
)
