"""规则集管理 API"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BizErrorCode, BizException, DuplicateException, NotFoundException
from app.db import get_db
from app.schemas.common import Page, ItemsResponse
from app.models.rule_set import RuleSet
from app.models.rule import Rule
from app.models.etl_job import ETLJob
from app.utils.sanitize import sanitize_user_input
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/rule-sets", tags=["规则集管理"])


# ── Schema ──

class RuleSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    color: str = Field(default="#1677ff", pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int = Field(default=0, ge=0)
    enabled: bool = True

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class RuleSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int | None = Field(default=None, ge=0)
    enabled: bool | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class RuleSetOut(BaseModel):
    """规则集响应；rule_count 由路由在 list/all/get 注入。"""
    id: str
    name: str
    description: str | None = None
    color: str
    sort_order: int
    enabled: bool
    rule_count: int | None = None
    created_at: datetime
    updated_at: datetime


# ── Routes ──

@router.get("", response_model=Page[RuleSetOut])
async def list_rule_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count(RuleSet.id)))
    total = count_result.scalar()

    # 单条 GROUP BY 查询消除 N+1：一次拿到所有规则集及其 rule_count
    result = await db.execute(
        select(
            RuleSet,
            func.count(Rule.id).label("rule_count"),
        )
        .outerjoin(Rule, Rule.rule_set_id == RuleSet.id)
        .group_by(RuleSet.id)
        .order_by(RuleSet.sort_order.asc(), RuleSet.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for rs, rule_count in result.all():
        rs.rule_count = rule_count
        items.append(rs)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/all", response_model=ItemsResponse[RuleSetOut])
async def list_all_rule_sets(db: AsyncSession = Depends(get_db)):
    """返回所有启用的规则集（下拉选择用）"""
    result = await db.execute(
        select(
            RuleSet,
            func.count(Rule.id).label("rule_count"),
        )
        .outerjoin(Rule, Rule.rule_set_id == RuleSet.id)
        .where(RuleSet.enabled == True)
        .group_by(RuleSet.id)
        .order_by(RuleSet.sort_order.asc(), RuleSet.name.asc())
    )
    items = []
    for rs, rule_count in result.all():
        rs.rule_count = rule_count
        items.append(rs)
    return {"items": items}


@router.get("/{rs_id}", response_model=RuleSetOut)
async def get_rule_set(rs_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise NotFoundException(detail="规则集不存在")
    cnt = await db.execute(
        select(func.count(Rule.id)).where(Rule.rule_set_id == rs.id)
    )
    rs.rule_count = cnt.scalar()
    return rs


@router.post("", status_code=201, response_model=RuleSetOut)
async def create_rule_set(body: RuleSetCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(RuleSet).where(RuleSet.name == body.name))
    if existing.scalar_one_or_none():
        raise DuplicateException(detail=f"规则集 '{body.name}' 已存在")

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
    return rs


@router.put("/{rs_id}", response_model=RuleSetOut)
async def update_rule_set(
    rs_id: str, body: RuleSetUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise NotFoundException(detail="规则集不存在")

    if body.name is not None:
        existing = await db.execute(
            select(RuleSet).where(RuleSet.name == body.name, RuleSet.id != rs_id)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(detail=f"规则集 '{body.name}' 已存在")
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
    return rs


@router.delete("/{rs_id}")
async def delete_rule_set(rs_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RuleSet).where(RuleSet.id == rs_id))
    rs = result.scalar_one_or_none()
    if not rs:
        raise NotFoundException(detail="规则集不存在")

    # 检查是否有规则引用
    cnt_result = await db.execute(
        select(func.count(Rule.id)).where(Rule.rule_set_id == rs_id)
    )
    rule_count = cnt_result.scalar()
    if rule_count > 0:
        raise BizException(
            code=BizErrorCode.BUSINESS_ERROR,
            detail=f"规则集 '{rs.name}' 下有 {rule_count} 条规则，请先移走或删除这些规则",
        )

    await db.delete(rs)
    await db.commit()
    return {"message": "ok"}
