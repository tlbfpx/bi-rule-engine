"""映射表管理 API"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger
import polars as pl

from app.db import get_db
from app.models.lookup_table import LookupTable
from app.schemas.lookup_table import LookupTableCreate, LookupTableUpdate, LookupTableOut
from app.schemas.common import Page

router = APIRouter()


@router.get("", response_model=Page[LookupTableOut])
async def list_lookup_tables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(LookupTable)
    count_query = select(func.count(LookupTable.id))
    if search:
        query = query.where(LookupTable.name.ilike(f"%{search}%"))
        count_query = count_query.where(LookupTable.name.ilike(f"%{search}%"))
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(LookupTable.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tables = result.scalars().all()
    return {"items": tables, "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201, response_model=LookupTableOut)
async def create_lookup_table(body: LookupTableCreate, db: AsyncSession = Depends(get_db)):
    table = LookupTable(
        name=body.name, description=body.description,
        source_type=body.source_type, columns=body.columns,
        data=body.data, row_count=len(body.data),
    )
    db.add(table)
    await db.flush()
    await db.refresh(table)
    logger.info(f"创建映射表: {table.name} ({table.row_count} 行)")
    return table


@router.post("/upload", status_code=201, response_model=LookupTableOut)
async def upload_lookup_table(
    name: str = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if file.filename and file.filename.endswith(".csv"):
        df = pl.read_csv(content)
    else:
        df = pl.read_excel(content)
    columns = {"key_col": df.columns[0], "value_col": df.columns[1] if len(df.columns) > 1 else df.columns[0]}
    data = {}
    for row in df.iter_rows(named=True):
        key = str(row[df.columns[0]]) if row[df.columns[0]] is not None else ""
        val = str(row[df.columns[1]]) if len(df.columns) > 1 and row[df.columns[1]] is not None else key
        data[key] = val
    table = LookupTable(name=name, source_type="upload", columns=columns, data=data, row_count=len(data))
    db.add(table)
    await db.flush()
    await db.refresh(table)
    logger.info(f"上传映射表: {table.name} ({table.row_count} 行)")
    return table


@router.get("/{table_id}", response_model=LookupTableOut)
async def get_lookup_table(table_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LookupTable).where(LookupTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="映射表不存在")
    return table


@router.put("/{table_id}", response_model=LookupTableOut)
async def update_lookup_table(table_id: str, body: LookupTableUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LookupTable).where(LookupTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="映射表不存在")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(table, key, value)
    if "data" in update_data:
        table.row_count = len(update_data["data"])
    await db.flush()
    await db.refresh(table)
    return table


@router.delete("/{table_id}", status_code=204)
async def delete_lookup_table(table_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LookupTable).where(LookupTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="映射表不存在")
    await db.delete(table)
