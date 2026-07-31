"""数据源 Repository 实现"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.data_source import DataSource


class DataSourceRepository(BaseRepository[DataSource]):
    """数据源仓储，提供按名称查询和启用列表。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, DataSource)

    async def find_by_name(self, name: str) -> DataSource | None:
        """根据名称查询数据源。

        Args:
            name: 数据源名称（唯一）

        Returns:
            数据源对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(DataSource).where(DataSource.name == name)
        )
        return result.scalar_one_or_none()

    async def find_enabled(self) -> list[DataSource]:
        """查询所有启用的数据源。

        Returns:
            启用的数据源列表
        """
        result = await self.db.execute(
            select(DataSource).where(DataSource.enabled.is_(True))
        )
        return list(result.scalars().all())
