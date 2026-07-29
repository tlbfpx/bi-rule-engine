"""任务管理 API"""
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from loguru import logger
import polars as pl

from app.db import get_db
from app.models.task import ExecutionTask
from app.schemas.task import TaskCreate, TaskOut
from app.schemas.common import Page
from app.services.execution_service import execute_dataframe

router = APIRouter()


@router.post("", status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = ExecutionTask(
        task_name=body.task_name or f"Task-{body.output_format}",
        source_id=body.source_id, template_id=body.template_id,
        query_params=body.query_params, output_format=body.output_format,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    logger.info(f"创建任务: {task.task_name}")
    return {"id": str(task.id), "task_name": task.task_name, "status": "pending"}


@router.post("/upload")
async def upload_and_preview(file: UploadFile = File(...)):
    content = await file.read()
    if file.filename and file.filename.endswith(".csv"):
        df = pl.read_csv(content)
    else:
        df = pl.read_excel(content)
    preview_rows = df.head(100).to_dicts()
    null_stats = {}
    for col in df.columns:
        null_count = df[col].null_count()
        null_stats[col] = {"null_count": null_count, "null_rate": round(null_count / len(df), 4) if len(df) > 0 else 0}
    return {
        "filename": file.filename, "total_rows": len(df), "total_columns": len(df.columns),
        "columns": df.columns, "preview_rows": preview_rows, "null_stats": null_stats,
    }


@router.post("/upload/execute")
async def execute_upload_task(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """上传文件并对全部启用规则执行（业务逻辑见 services.execution_service）。"""
    content = await file.read()
    if file.filename and file.filename.endswith(".csv"):
        df = pl.read_csv(content)
    else:
        df = pl.read_excel(content)
    return await execute_dataframe(db, df, file.filename)


@router.get("/{task_id}/status", response_model=TaskOut)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExecutionTask).where(ExecutionTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/{task_id}/download")
async def download_task_result(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExecutionTask).where(ExecutionTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    if task.output_file and os.path.exists(task.output_file):
        return FileResponse(task.output_file, filename=f"{task.task_name}.{task.output_format}")
    raise HTTPException(status_code=404, detail="输出文件不存在")


@router.get("", response_model=Page[TaskOut])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ExecutionTask)
    count_query = select(func.count(ExecutionTask.id))
    if status:
        query = query.where(ExecutionTask.status == status)
        count_query = count_query.where(ExecutionTask.status == status)
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ExecutionTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return {"items": tasks, "total": total, "page": page, "page_size": page_size}


@router.delete("/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExecutionTask).where(ExecutionTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.output_file and os.path.exists(task.output_file):
        os.remove(task.output_file)
    await db.delete(task)
    logger.info(f"删除任务: {task.task_name}")
    return {"id": task_id}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExecutionTask).where(ExecutionTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="只能取消等待中或运行中的任务")
    task.status = "failed"
    await db.flush()
    logger.info(f"取消任务: {task.task_name}")
    return {"id": task_id, "status": "failed"}
