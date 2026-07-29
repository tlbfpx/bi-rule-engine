"""规则管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.db import get_db
from app.models.rule import Rule
from app.schemas.rule import RuleCreate, RuleUpdate, RuleTestRequest, BatchPriorityUpdate, RuleOut
from app.schemas.common import Page
from app.services.rule_service import test_rule as run_rule_test

router = APIRouter()


@router.get("", response_model=Page[RuleOut])
async def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    field_name: str | None = None,
    rule_type: str | None = None,
    enabled: bool | None = None,
    rule_set_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Rule)
    count_query = select(func.count(Rule.id))
    if field_name:
        query = query.where(Rule.field_name.ilike(f"%{field_name}%"))
        count_query = count_query.where(Rule.field_name.ilike(f"%{field_name}%"))
    if rule_type:
        query = query.where(Rule.rule_type == rule_type)
        count_query = count_query.where(Rule.rule_type == rule_type)
    if enabled is not None:
        query = query.where(Rule.enabled == enabled)
        count_query = count_query.where(Rule.enabled == enabled)
    if rule_set_id:
        query = query.where(Rule.rule_set_id == rule_set_id)
        count_query = count_query.where(Rule.rule_set_id == rule_set_id)
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Rule.priority.asc(), Rule.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rules = result.scalars().all()

    # 批量加载规则集名称
    rule_set_ids = {r.rule_set_id for r in rules if r.rule_set_id}
    rule_set_names = {}
    if rule_set_ids:
        from app.models.rule_set import RuleSet
        rs_result = await db.execute(select(RuleSet).where(RuleSet.id.in_(rule_set_ids)))
        for rs in rs_result.scalars().all():
            rule_set_names[rs.id] = rs.name

    # 把规则集名作为动态属性附在 ORM 实例上，由 response_model(RuleOut) 序列化
    for r in rules:
        r.rule_set_name = rule_set_names.get(r.rule_set_id)

    return {"items": rules, "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201, response_model=RuleOut)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = Rule(
        rule_set_id=body.rule_set_id,
        field_name=body.field_name, field_label=body.field_label,
        rule_type=body.rule_type, priority=body.priority, enabled=body.enabled,
        config=body.config.model_dump(), lookup_table_id=body.lookup_table_id,
        depends_on=body.depends_on or [], description=body.description,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info(f"创建规则: {rule.field_name} ({rule.rule_type})")
    return rule


@router.put("/batch-priority")
async def batch_update_priority(body: BatchPriorityUpdate, db: AsyncSession = Depends(get_db)):
    for item in body.items:
        result = await db.execute(select(Rule).where(Rule.id == item["id"]))
        rule = result.scalar_one_or_none()
        if rule:
            rule.priority = item["priority"]
    await db.flush()
    return {"message": "ok", "count": len(body.items)}


@router.get("/{rule_id}", response_model=RuleOut)
async def get_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: str, body: RuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    update_data = body.model_dump(exclude_unset=True)
    if "config" in update_data and hasattr(update_data.get("config"), "model_dump"):
        update_data["config"] = update_data["config"].model_dump()
    for key, value in update_data.items():
        setattr(rule, key, value)
    await db.flush()
    await db.refresh(rule)
    logger.info(f"更新规则: {rule.field_name}")
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    logger.info(f"删除规则: {rule.field_name}")


@router.post("/{rule_id}/test")
async def test_rule(rule_id: str, body: RuleTestRequest, db: AsyncSession = Depends(get_db)):
    """试跑单条规则（业务逻辑见 services.rule_service）。"""
    return await run_rule_test(db, rule_id, body.test_rows)
