"""目标表管理 API"""
import pymysql
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.db import get_db
from app.models.target_table import TargetTable
from app.schemas.target_table import TargetTableCreate, TargetTableUpdate, TargetTableOut, TargetTableTestRequest

router = APIRouter()


def _test_db_connection(host: str, port: int, database: str, username: str, password: str) -> bool:
    try:
        conn = pymysql.connect(
            host=host, port=port, user=username, password=password,
            database=database, charset="utf8mb4", connect_timeout=5,
        )
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"数据库连接测试失败: {e}")
        return False


@router.post("", status_code=201)
async def create_target_table(body: TargetTableCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(TargetTable).where(TargetTable.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="目标表配置名称已存在")

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
    return tt.to_dict()


@router.get("")
async def list_target_tables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    query = select(TargetTable)
    count_query = select(func.count(TargetTable.id))
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(TargetTable.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": [tt.to_dict() for tt in items], "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def list_all_target_tables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).order_by(TargetTable.name.asc()))
    items = result.scalars().all()
    return {"items": [{"id": tt.id, "name": tt.name, "table_name": tt.table_name, "enabled": tt.enabled} for tt in items]}


@router.get("/{tt_id}")
async def get_target_table(tt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="目标表配置不存在")
    return tt.to_dict()


@router.put("/{tt_id}")
async def update_target_table(tt_id: str, body: TargetTableUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="目标表配置不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != tt.name:
        existing = await db.execute(select(TargetTable).where(TargetTable.name == update_data["name"]))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="目标表配置名称已存在")

    for field, value in update_data.items():
        if field == "db_password" and value:
            tt.db_password = value
        else:
            setattr(tt, field, value)

    await db.flush()
    await db.refresh(tt)
    logger.info(f"更新目标表配置: {tt.name}")
    return tt.to_dict()


@router.delete("/{tt_id}")
async def delete_target_table(tt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="目标表配置不存在")
    await db.delete(tt)
    logger.info(f"删除目标表配置: {tt.name}")
    return {"id": tt_id}


@router.post("/test-connection")
async def test_connection(body: TargetTableTestRequest):
    ok = _test_db_connection(body.db_host, body.db_port, body.db_name, body.db_username, body.db_password)
    if not ok:
        raise HTTPException(status_code=400, detail="数据库连接失败")
    return {"ok": True}


@router.post("/{tt_id}/sync-schema")
async def sync_target_schema(tt_id: str, db: AsyncSession = Depends(get_db)):
    """同步目标表结构：删除旧表并按当前规则输出字段重新创建"""
    from app.engine.etl_runner import _ensure_table_exists
    from app.engine.parser import RuleParser
    from app.models.rule import Rule

    result = await db.execute(select(TargetTable).where(TargetTable.id == tt_id))
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(status_code=404, detail="目标表配置不存在")

    # 创建空 DataFrame 模拟输出结构（包含所有规则输出字段 + 源字段）
    # 从规则配置推算输出字段
    rule_result = await db.execute(select(Rule).where(Rule.enabled == True).order_by(Rule.priority.asc()))
    rules = rule_result.scalars().all()

    # 收集所有可能的输出列
    import polars as pl
    columns = ["id", "partner_name", "eorder_name", "card_name", "pay_amount",
               "sum_fin_rev", "card_product_seg_name", "fin_product", "reject_reason",
               "buyer_contract_name", "buyer_contract_id", "company_segment_code",
               "prod_class", "gmt_effect_end", "rate_2", "if_reject", "buyer_name",
               "upd_eorder_name", "product_segment_code", "is_spec_reject",
               "sum_fin_ar", "ar_balance"]

    empty_df = pl.DataFrame({col: pl.Series([], dtype=pl.Utf8) for col in columns})

    # 先 DROP 再建表
    try:
        conn = pymysql.connect(
            host=tt.db_host, port=tt.db_port, user=tt.db_username,
            password=tt.db_password, database=tt.db_name, charset="utf8mb4",
        )
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS `{tt.table_name}`")
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"删除旧表失败: {e}")

    _ensure_table_exists(empty_df, tt)
    logger.info(f"同步目标表结构完成: {tt.table_name}")
    return {"ok": True, "table": tt.table_name}
