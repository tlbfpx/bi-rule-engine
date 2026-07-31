"""执行任务 Repository 实现"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.models.task import ExecutionTask


class TaskRepository(BaseRepository[ExecutionTask]):
    """执行任务仓储，提供按状态查询和最近任务列表。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ExecutionTask)

    async def find_by_status(self, status: str) -> list[ExecutionTask]:
        """根据状态查询执行任务列表，按创建时间倒序。

        Args:
            status: 任务状态（pending / running / completed / failed / cancelled）

        Returns:
            任务列表
        """
        result = await self.db.execute(
            select(ExecutionTask)
            .where(ExecutionTask.status == status)
            .order_by(ExecutionTask.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_recent(self, limit: int = 20) -> list[ExecutionTask]:
        """查询最近的执行任务，按创建时间倒序。

        Args:
            limit: 返回条数，默认 20

        Returns:
            最近的任务列表
        """
        result = await self.db.execute(
            select(ExecutionTask)
            .order_by(ExecutionTask.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
