"""映射表 Repository 实现"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.lookup_table import LookupTable


class LookupTableRepository(BaseRepository[LookupTable]):
    """映射表仓储，提供按名称查询和全量字典映射。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, LookupTable)

    async def find_by_name(self, name: str) -> LookupTable | None:
        """根据名称查询映射表。

        Args:
            name: 映射表名称（唯一）

        Returns:
            映射表对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(LookupTable).where(LookupTable.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_as_dict(self) -> dict[str, dict]:
        """查询全部映射表，构建 {id: data} 字典。

        用于规则引擎执行时快速查找映射数据。

        Returns:
            以 ID 字符串为 key、data 字段为 value 的字典
        """
        result = await self.db.execute(select(LookupTable))
        tables = result.scalars().all()
        return {str(table.id): table.data for table in tables}
