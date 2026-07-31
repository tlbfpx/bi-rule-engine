"""目标表 Repository 实现"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.target_table import TargetTable


class TargetTableRepository(BaseRepository[TargetTable]):
    """目标表仓储，提供按名称查询。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, TargetTable)

    async def find_by_name(self, name: str) -> TargetTable | None:
        """根据名称查询目标表。

        Args:
            name: 目标表名称（唯一）

        Returns:
            目标表对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(TargetTable).where(TargetTable.name == name)
        )
        return result.scalar_one_or_none()
