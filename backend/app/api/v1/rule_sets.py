"""规则集管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.rule_set import RuleSet
from app.models.rule import Rule
from app.models.etl_job import ETLJob
from pydantic import BaseModel, Field

router = APIRouter(prefix="/rule-sets", tags=["规则集管理"])


# ── Schema ──

class RuleSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    color: str = "#1677ff"
    sort_order: int = 0
    enabled: bool = True


class RuleSetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None


# ── Routes ──

@router.get("")
async def list_rule_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count(RuleSet.id)))
    total = count_result.scalar()

    result = await db.execute(
        select(RuleSet)
        .order_by(RuleSet.sort_order.asc(), RuleSet.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for rs in result.scalars().all():
        d = rs.to_dict()
        # 统计规则数量
        cnt = await db.execute(
            select(func.count(Rule.id)).where(Rule.rule_set_id == rs.id)
        )
        d["rule_count"] = cnt.scalar()
        items.append(d)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all")
async def list_all_rule_sets(db: AsyncSession = Depends(get_db)):
    """返回所有启用的规则集（下拉选择用）"""
    result = await db.execute(
        select(RuleSet)
        .where(RuleSet.enabled == True)
        .order_by(RuleSet.sort_order.asc(), RuleSet.name.asc())
    )
    items = []
    for rs in result.scalars().all():
        d = rs.to_dict()
        cnt = await db.execute(
            select(func.count(Rule.id)).where(Rule.rule_set_id == rs.id)
        )
        d["rule_count"] = cnt.scalar()
        items.append(d)
    return {"items": items}


@router.get("/{rs_id}")
async def get_rule_set(rs_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="规则集不存在")
    d = rs.to_dict()
    cnt = await db.execute(
        select(func.count(Rule.id)).where(Rule.rule_set_id == rs.id)
    )
    d["rule_count"] = cnt.scalar()
    return d


@router.post("", status_code=201)
async def create_rule_set(body: RuleSetCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(RuleSet).where(RuleSet.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"规则集 '{body.name}' 已存在")

    rs = RuleSet(
        name=body.name,
        description=body.description,
        color=body.color,
        sort_order=body.sort_order,
        enabled=body.enabled,
    )
    db.add(rs)
    await db.commit()
    await db.refresh(rs)
    return rs.to_dict()


@router.put("/{rs_id}")
async def update_rule_set(
    rs_id: str, body: RuleSetUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="规则集不存在")

    if body.name is not None:
        existing = await db.execute(
            select(RuleSet).where(RuleSet.name == body.name, RuleSet.id != rs_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"规则集 '{body.name}' 已存在")
        rs.name = body.name
    if body.description is not None:
        rs.description = body.description
    if body.color is not None:
        rs.color = body.color
    if body.sort_order is not None:
        rs.sort_order = body.sort_order
    if body.enabled is not None:
        rs.enabled = body.enabled

    await db.commit()
    await db.refresh(rs)
    return rs.to_dict()


@router.delete("/{rs_id}")
async def delete_rule_set(rs_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="规则集不存在")

    # 检查是否有规则引用
    cnt_result = await db.execute(
        select(func.count(Rule.id)).where(Rule.rule_set_id == rs_id)
    )
    rule_count = cnt_result.scalar()
    if rule_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"规则集 '{rs.name}' 下有 {rule_count} 条规则，请先移走或删除这些规则",
        )

    await db.delete(rs)
    await db.commit()
    return {"message": "ok"}
