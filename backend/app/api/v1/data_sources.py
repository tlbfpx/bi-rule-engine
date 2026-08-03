"""数据源管理 API"""
import pymysql
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.exceptions import BizErrorCode, BizException, DuplicateException, NotFoundException
from app.db import get_db
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate, DataSourceOut, DataSourceTestRequest
from app.schemas.common import Page
from app.utils.crypto import encrypt

router = APIRouter()


def _test_db_connection(host: str, port: int, database: str, username: str, password: str) -> bool:
    conn = None
    try:
        conn = pymysql.connect(
            host=host, port=port, user=username, password=password,
            database=database, charset="utf8mb4", connect_timeout=5,
        )
        return True
    except Exception as e:
        logger.warning(f"数据库连接测试失败: {e}")
        return False
    finally:
        if conn:
            conn.close()


@router.post("", status_code=201, response_model=DataSourceOut)
async def create_data_source(body: DataSourceCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(DataSource).where(DataSource.name == body.name))
    if existing.scalar_one_or_none():
        raise DuplicateException(detail="数据源名称已存在")

    ds = DataSource(
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        db_host=body.db_host,
        db_port=body.db_port,
        db_name=body.db_name,
        db_username=body.db_username,
        db_password=body.db_password,
        extract_mode=body.extract_mode,
        extract_sql=body.extract_sql,
        extract_table=body.extract_table,
        incremental_column=body.incremental_column,
        incremental_value=body.incremental_value,
    )
    db.add(ds)
    await db.flush()
    await db.refresh(ds)
    logger.info(f"创建数据源: {ds.name}")
    return ds


@router.get("", response_model=Page[DataSourceOut])
async def list_data_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(DataSource)
    count_query = select(func.count(DataSource.id))
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(DataSource.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def list_all_data_sources(db: AsyncSession = Depends(get_db)):
    """返回所有数据源，用于下拉选择"""
    result = await db.execute(select(DataSource).order_by(DataSource.name.asc()))
    items = result.scalars().all()
    return {"items": [{"id": ds.id, "name": ds.name, "enabled": ds.enabled} for ds in items]}


@router.get("/{ds_id}", response_model=DataSourceOut)
async def get_data_source(ds_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise NotFoundException(detail="数据源不存在")
    return ds


@router.put("/{ds_id}", response_model=DataSourceOut)
async def update_data_source(ds_id: str, body: DataSourceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise NotFoundException(detail="数据源不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != ds.name:
        existing = await db.execute(select(DataSource).where(DataSource.name == update_data["name"]))
        if existing.scalar_one_or_none():
            raise DuplicateException(detail="数据源名称已存在")

    for field, value in update_data.items():
        if field == "db_password" and value:
            ds.db_password = value
        else:
            setattr(ds, field, value)

    await db.flush()
    await db.refresh(ds)
    logger.info(f"更新数据源: {ds.name}")
    return ds


@router.delete("/{ds_id}")
async def delete_data_source(ds_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise NotFoundException(detail="数据源不存在")
    await db.delete(ds)
    logger.info(f"删除数据源: {ds.name}")
    return {"id": ds_id}


@router.post("/test-connection")
async def test_connection(body: DataSourceTestRequest):
    ok = _test_db_connection(body.db_host, body.db_port, body.db_name, body.db_username, body.db_password)
    if not ok:
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail="数据库连接失败")
    return {"ok": True}


@router.post("/{ds_id}/preview")
async def preview_data_source(ds_id: str, limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    from app.engine.etl_runner import _build_extract_sql
    from app.utils.mysql_reader import read_mysql_query

    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise NotFoundException(detail="数据源不存在")

    try:
        sql, params = _build_extract_sql(ds)
        # 添加参数化 LIMIT（安全：避免字符串拼接）
        preview_sql = f"{sql} LIMIT :preview_limit"
        preview_params = {**(params or {}), "preview_limit": limit}
        df = read_mysql_query(
            host=ds.db_host, port=ds.db_port, database=ds.db_name,
            username=ds.db_username, password=ds.db_password,
            query=preview_sql,
            params=preview_params,
        )
        # 构建列画像
        column_profiles = {}
        for col in df.columns:
            series = df[col]
            null_count = int(series.isnull().sum() if hasattr(series, 'isnull') else 0)
            sample_vals = series.dropna().head(3).tolist() if hasattr(series, 'dropna') else []
            distinct_val = int(series.nunique()) if hasattr(series, 'nunique') else 0
            dtype = str(series.dtype) if hasattr(series, 'dtype') else 'object'
            column_profiles[col] = {
                "null_rate": round(null_count / max(len(df), 1), 4),
                "distinct_count": distinct_val,
                "sample_values": [str(v) for v in sample_vals],
                "dtype": dtype,
            }
        return {
            "sql": preview_sql,
            "total_rows": len(df),
            "columns": df.columns,
            "preview_rows": df.head(limit).to_dicts(),
            "column_profiles": column_profiles,
        }
    except Exception as e:
        logger.exception("数据源预览失败")
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail=f"预览失败: {e}")
