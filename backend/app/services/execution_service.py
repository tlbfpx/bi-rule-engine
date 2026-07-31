"""执行服务 — 向下兼容适配层。

业务逻辑已迁移到 app.application.services.ExecutionService
（Template Method + Command Pattern），本模块保留旧函数签名，
通过创建 Repository 适配器委托到新服务，确保 API 层无需修改。
"""
from __future__ import annotations

import polars as pl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_service import (
    ExecutionService,
    LookupTableRepository,
    RuleRepository,
    TaskRepository,
)
from app.models.lookup_table import LookupTable
from app.models.rule import Rule
from app.models.task import ExecutionTask

__all__ = ["execute_dataframe"]


class _SqlAlchemyRuleRepository:
    """规则仓储适配器 — 查询启用规则。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_all_enabled(self) -> list[Rule]:
        result = await self._db.execute(
            select(Rule).where(Rule.enabled == True).order_by(Rule.priority.asc())  # noqa: E712
        )
        return result.scalars().all()


class _SqlAlchemyLookupTableRepository:
    """映射表仓储适配器。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_all(self) -> list[LookupTable]:
        result = await self._db.execute(select(LookupTable))
        return result.scalars().all()


class _SqlAlchemyTaskRepository:
    """任务仓储适配器。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, entity: ExecutionTask) -> ExecutionTask:
        self._db.add(entity)
        await self._db.flush()
        await self._db.refresh(entity)
        return entity


async def execute_dataframe(
    db: AsyncSession,
    df: pl.DataFrame,
    source_name: str,
) -> dict:
    """对 DataFrame 跑全部启用规则，落 ExecutionTask，返回结果摘要 + 预览。

    委托到 ExecutionService.execute_dataframe，保持与旧接口完全兼容。
    db 参数传递给 Repository 适配器，不再传入 execute_dataframe。
    """
    service = ExecutionService(
        rule_repo=_SqlAlchemyRuleRepository(db),
        lookup_table_repo=_SqlAlchemyLookupTableRepository(db),
        task_repo=_SqlAlchemyTaskRepository(db),
    )
    return await service.execute_dataframe(df, source_name)
