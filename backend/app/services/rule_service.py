"""规则领域服务 — 向下兼容适配层。

业务逻辑已迁移到 app.application.services.RuleService（Facade Pattern），
本模块保留旧函数签名，通过创建 Repository 适配器委托到新服务，
确保 API 层无需修改。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.rule_service import RuleRepository, RuleService
from app.models.rule import Rule

__all__ = ["test_rule"]


class _SqlAlchemyRuleRepository:
    """SQLAlchemy 规则仓储适配器 — 将 AsyncSession 适配为 RuleRepository 接口。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_by_id(self, id: str) -> Rule | None:
        result = await self._db.execute(select(Rule).where(Rule.id == id))
        return result.scalar_one_or_none()

    async def find_all(
        self,
        *conditions: Any,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Rule], int]:
        query = select(Rule)
        count_query = select(func.count(Rule.id))
        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)
        total = (await self._db.execute(count_query)).scalar()
        query = query.order_by(Rule.priority.asc(), Rule.updated_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self._db.execute(query)
        return result.scalars().all(), total

    async def save(self, entity: Rule) -> Rule:
        self._db.add(entity)
        await self._db.flush()
        await self._db.refresh(entity)
        return entity

    async def update(self, entity: Rule, **data: Any) -> Rule:
        for key, value in data.items():
            setattr(entity, key, value)
        await self._db.flush()
        await self._db.refresh(entity)
        return entity

    async def delete(self, entity: Rule) -> None:
        await self._db.delete(entity)


async def test_rule(db: AsyncSession, rule_id: str, test_rows: list[dict]) -> dict:
    """对单条规则用测试数据试跑，返回逐行结果 + 汇总统计。

    委托到 RuleService.test_rule，保持与旧接口完全兼容。
    """
    repo = _SqlAlchemyRuleRepository(db)
    service = RuleService(repo)
    return await service.test_rule(rule_id, test_rows, db)
