"""ETL 调度任务 Repository 实现"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.repository import BaseRepository
from app.models.etl_job import ETLJob


class ETLJobRepository(BaseRepository[ETLJob]):
    """ETL 调度任务仓储，提供启用列表、按数据源查询及运行状态更新。"""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ETLJob)

    async def find_enabled(self) -> list[ETLJob]:
        """查询所有启用的 ETL 调度任务。

        Returns:
            启用的调度任务列表
        """
        result = await self.db.execute(
            select(ETLJob).where(ETLJob.enabled.is_(True))
        )
        return list(result.scalars().all())

    async def find_by_data_source(self, data_source_id: str) -> list[ETLJob]:
        """根据数据源 ID 查询关联的调度任务。

        Args:
            data_source_id: 数据源 ID

        Returns:
            调度任务列表
        """
        result = await self.db.execute(
            select(ETLJob).where(ETLJob.data_source_id == data_source_id)
        )
        return list(result.scalars().all())

    async def update_run_status(
        self,
        job_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """更新调度任务的最近运行状态。

        Args:
            job_id: 调度任务 ID
            status: 运行状态
            error: 错误信息（可选）

        Raises:
            NotFoundException: 调度任务不存在
        """
        exists_result = await self.db.execute(
            select(ETLJob.id).where(ETLJob.id == job_id).limit(1)
        )
        if exists_result.scalar_one_or_none() is None:
            raise NotFoundException(detail=f"ETL 调度任务不存在: {job_id}")

        values: dict = {
            "last_run_at": datetime.now(timezone.utc),
            "last_run_status": status,
        }
        if error is not None:
            values["last_run_error"] = error

        stmt = update(ETLJob).where(ETLJob.id == job_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()
