"""规则 Repository 实现"""
from typing import Any

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.rule import Rule


class RuleRepository(BaseRepository[Rule]):
    """规则仓储，提供按规则集、启用状态、类型的查询及批量优先级更新。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Rule)

    async def find_by_rule_set(self, rule_set_id: str) -> list[Rule]:
        """根据规则集 ID 查询规则列表，按优先级升序。

        Args:
            rule_set_id: 规则集 ID

        Returns:
            规则列表
        """
        result = await self.db.execute(
            select(Rule)
            .where(Rule.rule_set_id == rule_set_id)
            .order_by(Rule.priority.asc())
        )
        return list(result.scalars().all())

    async def find_enabled(self) -> list[Rule]:
        """查询所有启用的规则，按优先级升序。

        Returns:
            启用的规则列表
        """
        result = await self.db.execute(
            select(Rule).where(Rule.enabled.is_(True)).order_by(Rule.priority.asc())
        )
        return list(result.scalars().all())

    async def find_by_type(self, rule_type: str) -> list[Rule]:
        """根据规则类型查询规则列表。

        Args:
            rule_type: 规则类型（mapping / cleaning / lookup / computed）

        Returns:
            规则列表
        """
        result = await self.db.execute(
            select(Rule).where(Rule.rule_type == rule_type)
        )
        return list(result.scalars().all())

    async def batch_update_priority(self, items: list[dict[str, Any]]) -> None:
        """批量更新规则优先级。

        使用 CASE WHEN 单次 SQL 完成批量更新。

        Args:
            items: 每项包含 id 和 priority，如 {"id": "...", "priority": 10}
        """
        if not items:
            return

        id_to_priority: dict[str, int] = {
            item["id"]: item["priority"] for item in items
        }
        stmt = (
            update(Rule)
            .where(Rule.id.in_(id_to_priority.keys()))
            .values(priority=case(id_to_priority, value=Rule.id))
        )
        await self.db.execute(stmt)
        await self.db.flush()
