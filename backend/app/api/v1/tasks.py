"""任务管理 API"""
import os

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from loguru import logger
import polars as pl

from app.core.exceptions import BizErrorCode, BizException, NotFoundException, ValidationException
from app.db import get_db
from app.models.task import ExecutionTask
from app.schemas.task import TaskCreate, TaskOut
from app.schemas.common import Page
from app.services.execution_service import execute_dataframe
from app.config import get_settings

router = APIRouter()

# 允许的文件类型白名单
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _validate_upload_file(file: UploadFile) -> None:
    """校验上传文件的扩展名、MIME 类型和大小限制。"""
    settings = get_settings()
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # 1. 校验文件扩展名
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BizException(
            code=BizErrorCode.BUSINESS_ERROR,
            detail=f"不支持的文件类型: {ext}。仅允许 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 2. 校验 Content-Type（宽松匹配，允许 application/csv 等变体）
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        # CSV 文件有时以 application/octet-stream 上传，对此只做警告不做拒绝
        if content_type not in ("application/octet-stream", ""):
            raise BizException(
                code=BizErrorCode.BUSINESS_ERROR,
                detail=f"不支持的文件类型: {content_type}。仅允许 CSV 和 Excel 文件",
            )

    # 3. 校验文件名安全性（防止路径穿越、null 字节等）
    if "\x00" in filename or "/" in filename or "\\" in filename:
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail="文件名包含非法字符")


async def _read_and_validate_size(file: UploadFile) -> bytes:
    """读取文件内容并校验大小"""
    settings = get_settings()
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    content = await file.read()
    if len(content) > max_size_bytes:
        raise ValidationException(
            detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB）",
        )
    return content


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
    _validate_upload_file(file)
    content = await _read_and_validate_size(file)
    if file.filename and file.filename.endswith(".csv"):
        df = pl.read_csv(content)
    else:
        df = pl.read_excel(content)

    total_len = len(df)
    preview_rows = df.head(100).to_dicts()

    # 空值统计
    null_stats = {}
    for col in df.columns:
        null_count = df[col].null_count()
        null_stats[col] = {
            "null_count": null_count,
            "null_rate": round(null_count / total_len, 4) if total_len > 0 else 0,
        }

    # 列画像：为规则编辑器提供数据上下文
    profile_sample = df if total_len <= 5000 else df.sample(5000)
    column_profiles = {}
    for col in df.columns:
        series = profile_sample[col]
        distinct_count = series.n_unique()
        # Top 5 高频值
        try:
            vc = series.value_counts().sort("count", descending=True).head(5)
            top_values = [
                {"value": str(row[0]) if row[0] is not None else None, "count": row[1]}
                for row in vc.iter_rows()
            ]
        except Exception:
            top_values = []
        # 前3个非空样本值
        non_null_series = series.drop_nulls()
        sample_values = [str(v) for v in non_null_series.head(3).to_list()]
        column_profiles[col] = {
            "distinct_count": distinct_count,
            "top_values": top_values,
            "sample_values": sample_values,
            "null_rate": round(series.null_count() / len(series), 4) if len(series) > 0 else 0,
            "dtype": str(series.dtype),
        }

    return {
        "filename": file.filename,
        "total_rows": total_len,
        "total_columns": len(df.columns),
        "columns": df.columns,
        "preview_rows": preview_rows,
        "null_stats": null_stats,
        "column_profiles": column_profiles,
    }


@router.post("/upload/execute")
async def execute_upload_task(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """上传文件并对全部启用规则执行（业务逻辑见 services.execution_service）。"""
    _validate_upload_file(file)
    content = await _read_and_validate_size(file)
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
        raise NotFoundException(detail="任务不存在")
    return task


@router.get("/{task_id}/download")
async def download_task_result(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExecutionTask).where(ExecutionTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException(detail="任务不存在")
    if task.status != "completed":
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail="任务尚未完成")
    if task.output_file and os.path.exists(task.output_file):
        return FileResponse(task.output_file, filename=f"{task.task_name}.{task.output_format}")
    raise NotFoundException(detail="输出文件不存在")


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
        raise NotFoundException(detail="任务不存在")
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
        raise NotFoundException(detail="任务不存在")
    if task.status not in ("pending", "running"):
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail="只能取消等待中或运行中的任务")
    task.status = "cancelled"
    await db.flush()
    logger.info(f"取消任务: {task.task_name}")
    return {"id": task_id, "status": "cancelled"}
