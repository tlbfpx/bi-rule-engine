"""目标表管理 API"""
import pymysql
import polars as pl
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.exceptions import BizErrorCode, BizException, DuplicateException, NotFoundException
from app.db import get_db
from app.models.target_table import TargetTable
from app.schemas.target_table import TargetTableCreate, TargetTableUpdate, TargetTableOut, TargetTableTestRequest
from app.schemas.common import Page

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


@router.post("", status_code=201, response_model=TargetTableOut)
async def create_target_table(body: TargetTableCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(TargetTable).where(TargetTable.name == body.name))
    if existing.scalar_one_or_none():
        raise DuplicateException(detail="目标表配置名称已存在")

    tt = TargetTable(
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        db_host=body.db_host,
        db_port=body.db_port,
        db_name=body.db_name,
        db_username=body.db_username,
        db_password=body.db_password,
        table_name=body.table_name,
        write_mode=body.write_mode,
        upsert_keys=body.upsert_keys,
        auto_create_table=body.auto_create_table,
    )
    db.add(tt)
    await db.flush()
    await db.refresh(tt)
    logger.info(f"创建目标表配置: {tt.name}")
    return tt


@router.get("", response_model=Page[TargetTableOut])
async def list_target_tables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(TargetTable)
    count_query = select(func.count(TargetTable.id))
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(TargetTable.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def list_all_target_tables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).order_by(TargetTable.name.asc()))
    items = result.scalars().all()
    return {"items": [{"id": tt.id, "name": tt.name, "table_name": tt.table_name, "enabled": tt.enabled} for tt in items]}


@router.get("/{tt_id}", response_model=TargetTableOut)
async def get_target_table(tt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise NotFoundException(detail="目标表配置不存在")
    return tt


@router.put("/{tt_id}", response_model=TargetTableOut)
async def update_target_table(tt_id: str, body: TargetTableUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise NotFoundException(detail="目标表配置不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != tt.name:
        existing = await db.execute(select(TargetTable).where(TargetTable.name == update_data["name"]))
        if existing.scalar_one_or_none():
            raise DuplicateException(detail="目标表配置名称已存在")

    for field, value in update_data.items():
        if field == "db_password" and value:
            tt.db_password = value
        else:
            setattr(tt, field, value)

    await db.flush()
    await db.refresh(tt)
    logger.info(f"更新目标表配置: {tt.name}")
    return tt


@router.delete("/{tt_id}")
async def delete_target_table(tt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise NotFoundException(detail="目标表配置不存在")
    await db.delete(tt)
    logger.info(f"删除目标表配置: {tt.name}")
    return {"id": tt_id}


@router.post("/test-connection")
async def test_connection(body: TargetTableTestRequest):
    ok = _test_db_connection(body.db_host, body.db_port, body.db_name, body.db_username, body.db_password)
    if not ok:
        raise BizException(code=BizErrorCode.BUSINESS_ERROR, detail="数据库连接失败")
    return {"ok": True}


@router.post("/{tt_id}/sync-schema")
async def sync_target_schema(tt_id: str, db: AsyncSession = Depends(get_db)):
    """同步目标表结构：删除旧表并按当前规则输出字段重新创建

    输出字段从关联该目标表的 ETLJob → rule_set → Rule.field_name 动态推算，
    而不是硬编码业务字段名。
    """
    from app.engine.etl_runner import _ensure_table_exists
    from app.models.rule import Rule
    from app.models.etl_job import ETLJob
    from sqlalchemy import distinct

    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise NotFoundException(detail="目标表配置不存在")

    # 从关联该目标表的 ETLJob → rule_set → Rule 动态推算输出字段
    job_result = await db.execute(
        select(ETLJob.rule_set_id).where(ETLJob.target_table_id == tt_id)
    )
    rule_set_ids = [row[0] for row in job_result.all() if row[0]]

    output_columns = []
    if rule_set_ids:
        rule_result = await db.execute(
            select(distinct(Rule.field_name))
            .where(Rule.rule_set_id.in_(rule_set_ids), Rule.enabled == True)
            .order_by(Rule.field_name)
        )
        output_columns = [row[0] for row in rule_result.all()]

    # 如果没有关联规则，至少包含一个占位列
    if not output_columns:
        raise BizException(
            code=BizErrorCode.BUSINESS_ERROR,
            detail=f"目标表 '{tt.name}' 未关联任何启用规则的 ETL 任务，无法推断输出字段",
        )

    empty_df = pl.DataFrame({col: pl.Series([], dtype=pl.Utf8) for col in output_columns})

    # 先 DROP 再建表
    try:
        conn = pymysql.connect(
            host=tt.db_host, port=tt.db_port, user=tt.db_username,
            password=tt.db_password, database=tt.db_name, charset="utf8mb4",
            connect_timeout=10,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS `{tt.table_name}`")
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"删除旧表失败: {e}")

    _ensure_table_exists(empty_df, tt)
    logger.info(f"同步目标表结构完成: {tt.table_name}, 输出字段={output_columns}")
    return {"ok": True, "table": tt.table_name, "columns": output_columns}
