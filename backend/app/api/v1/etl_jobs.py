"""ETL 调度任务 API"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.db import get_db
from app.models.etl_job import ETLJob
from app.models.etl_job_run import ETLJobRun
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate, ETLJobOut, ETLJobRunOut
from app.schemas.common import Page
from app.engine.etl_runner import run_etl_job
from app.tasks.scheduler import scheduler_manager

router = APIRouter()


def _is_valid_cron(cron: str) -> bool:
    """简单校验 cron 表达式：5 个字段"""
    parts = cron.strip().split()
    return len(parts) == 5


@router.post("", status_code=201, response_model=ETLJobOut)
async def create_etl_job(body: ETLJobCreate, db: AsyncSession = Depends(get_db)):
    if not _is_valid_cron(body.cron_expression):
        raise HTTPException(status_code=400, detail="cron 表达式格式错误，需要 5 个字段（分 时 日 月 周）")

    job = ETLJob(
        job_name=body.job_name,
        description=body.description,
        enabled=body.enabled,
        data_source_id=body.data_source_id,
        target_table_id=body.target_table_id,
        rule_set_id=body.rule_set_id,
        cron_expression=body.cron_expression,
        timezone=body.timezone,
        error_retry_count=body.error_retry_count,
        timeout_seconds=body.timeout_seconds,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    if job.enabled:
        await scheduler_manager.add_job(job)

    logger.info(f"创建 ETL 任务: {job.job_name}")
    return job


@router.get("", response_model=Page[ETLJobOut])
async def list_etl_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    query = select(ETLJob)
    count_query = select(func.count(ETLJob.id))
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ETLJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/runs/{run_id}", response_model=ETLJobRunOut)
async def get_etl_job_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ETLJobRun).where(ETLJobRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return run


@router.get("/runs", response_model=Page[ETLJobRunOut])
async def list_all_etl_job_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """查询所有 ETL 执行历史"""
    query = select(ETLJobRun)
    count_query = select(func.count(ETLJobRun.id))
    if status:
        query = query.where(ETLJobRun.status == status)
        count_query = count_query.where(ETLJobRun.status == status)
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ETLJobRun.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{job_id}", response_model=ETLJobOut)
async def get_etl_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ETLJob).where(ETLJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="ETL 任务不存在")
    return job


@router.put("/{job_id}", response_model=ETLJobOut)
async def update_etl_job(job_id: str, body: ETLJobUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ETLJob).where(ETLJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="ETL 任务不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "cron_expression" in update_data and not _is_valid_cron(update_data["cron_expression"]):
        raise HTTPException(status_code=400, detail="cron 表达式格式错误")

    for field, value in update_data.items():
        setattr(job, field, value)

    await db.flush()
    await db.refresh(job)

    # 同步调度器
    await scheduler_manager.reschedule_job(job)

    logger.info(f"更新 ETL 任务: {job.job_name}")
    return job


@router.delete("/{job_id}")
async def delete_etl_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ETLJob).where(ETLJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="ETL 任务不存在")

    await scheduler_manager.remove_job(job_id)
    await db.delete(job)
    logger.info(f"删除 ETL 任务: {job.job_name}")
    return {"id": job_id}


@router.post("/{job_id}/run")
async def run_etl_job_manual(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ETLJob).where(ETLJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="ETL 任务不存在")

    # 创建执行记录并立即提交，确保后台任务能读取到
    run_record = ETLJobRun(etl_job_id=job_id, status="pending")
    db.add(run_record)
    await db.flush()
    await db.refresh(run_record)
    await db.commit()

    # 后台执行
    background_tasks.add_task(run_etl_job, job_id, str(run_record.id))

    logger.info(f"手动触发 ETL 任务: {job.job_name}, run_id={run_record.id}")
    return {"run_id": str(run_record.id), "status": "pending"}


@router.post("/{job_id}/toggle", response_model=ETLJobOut)
async def toggle_etl_job(job_id: str, enabled: bool, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ETLJob).where(ETLJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="ETL 任务不存在")

    job.enabled = enabled
    await db.flush()
    await db.refresh(job)

    if enabled:
        await scheduler_manager.add_job(job)
    else:
        await scheduler_manager.remove_job(job_id)

    logger.info(f"{'启用' if enabled else '停用'} ETL 任务: {job.job_name}")
    return job


@router.get("/{job_id}/runs", response_model=Page[ETLJobRunOut])
async def list_etl_job_runs(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    query = select(ETLJobRun).where(ETLJobRun.etl_job_id == job_id)
    count_query = select(func.count(ETLJobRun.id)).where(ETLJobRun.etl_job_id == job_id)
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ETLJobRun.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

