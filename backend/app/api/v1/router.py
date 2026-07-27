"""API v1 路由聚合"""
from fastapi import APIRouter
from app.api.v1 import rules, lookup_tables, tasks, data_sources, target_tables, etl_jobs, logs, rule_sets

api_router = APIRouter()
api_router.include_router(rules.router, prefix="/rules", tags=["规则管理"])
api_router.include_router(rule_sets.router, tags=["规则集管理"])
api_router.include_router(lookup_tables.router, prefix="/lookup-tables", tags=["映射表管理"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(data_sources.router, prefix="/data-sources", tags=["数据源管理"])
api_router.include_router(target_tables.router, prefix="/target-tables", tags=["目标表管理"])
api_router.include_router(etl_jobs.router, prefix="/etl-jobs", tags=["ETL 调度任务"])
api_router.include_router(logs.router, tags=["日志上报"])
