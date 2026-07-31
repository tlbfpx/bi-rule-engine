"""规则集 Repository 实现"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.rule import Rule
from app.models.rule_set import RuleSet


class RuleSetRepository(BaseRepository[RuleSet]):
    """规则集仓储，提供按名称查询、启用列表及规则数统计。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, RuleSet)

    async def find_by_name(self, name: str) -> RuleSet | None:
        """根据名称查询规则集。

        Args:
            name: 规则集名称（唯一）

        Returns:
            规则集对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.name == name)
        )
        return result.scalar_one_or_none()

    async def find_enabled(self) -> list[RuleSet]:
        """查询所有启用的规则集，按排序字段升序。

        Returns:
            启用的规则集列表
        """
        result = await self.db.execute(
            select(RuleSet)
            .where(RuleSet.enabled.is_(True))
            .order_by(RuleSet.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_rule_count(self, rule_set_id: str) -> int:
        """统计规则集下的规则数量。

        Args:
            rule_set_id: 规则集 ID

        Returns:
            规则数量
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(Rule)
            .where(Rule.rule_set_id == rule_set_id)
        )
        return result.scalar_one()
