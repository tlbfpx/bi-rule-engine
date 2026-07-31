"""执行服务 — Template Method + Command Pattern。

将 DataFrame 规则执行流程模板方法化：加载规则 → 执行转换 → 落库记录。
通过 Command 模式封装执行操作，支持撤销和重做。

兼容性：旧 app/services/execution_service.py 的 execute_dataframe 函数
委托到本服务，确保 API 层无需修改。
"""
from __future__ import annotations

import time
from typing import Any, Protocol, runtime_checkable

import polars as pl
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.executor import RuleExecutor
from app.engine.parser import RuleParser
from app.models.lookup_table import LookupTable
from app.models.rule import Rule
from app.models.task import ExecutionTask
from app.patterns.command import CommandInvoker
from app.patterns.template import BaseTemplate

__all__ = [
    "LookupTableRepository",
    "TaskRepository",
    "RuleRepository",
    "DataFrameTransformTemplate",
    "ExecuteDataFrameCommand",
    "ExecutionService",
]


# ───────────────────────── Repository 接口 ─────────────────────────


@runtime_checkable
class RuleRepository(Protocol):
    """规则仓储接口。"""

    async def find_all_enabled(self) -> list[Rule]:
        """查询所有启用的规则，按优先级升序。"""
        ...


@runtime_checkable
class LookupTableRepository(Protocol):
    """映射表仓储接口。"""

    async def find_all(self) -> list[LookupTable]:
        """查询所有映射表。"""
        ...


@runtime_checkable
class TaskRepository(Protocol):
    """执行任务仓储接口。"""

    async def save(self, entity: ExecutionTask) -> ExecutionTask:
        """保存任务记录。"""
        ...


# ───────────────────────── Template Method ─────────────────────────


class DataFrameTransformTemplate(BaseTemplate[dict]):
    """DataFrame 转换模板方法 — 同步部分。

    将规则执行的核心流程封装为模板方法：
    before() → 校验 DataFrame
    do_execute() → 执行规则转换
    after() → 记录统计日志

    Attributes:
        rule_configs: 解析后的规则配置列表
        lookup_tables: 映射表数据字典
        df: 待转换的 DataFrame
    """

    def __init__(
        self,
        rule_configs: list[RuleParser.__class__] | list[Any],
        lookup_tables: dict[str, dict],
        df: pl.DataFrame,
    ) -> None:
        self.rule_configs = rule_configs
        self.lookup_tables = lookup_tables
        self.df = df
        self._start_time: float = 0.0

    def before(self, **kwargs: Any) -> None:
        """前置校验 — 确保 DataFrame 非空。"""
        self._start_time = time.time()
        if self.df.is_empty():
            logger.warning("输入 DataFrame 为空，跳过规则执行")
        else:
            logger.info(
                f"开始执行 DataFrame 转换: {len(self.df)} 行, "
                f"{len(self.rule_configs)} 条规则"
            )

    def do_execute(self, **kwargs: Any) -> dict:
        """核心逻辑 — 执行规则转换。

        Returns:
            包含 result_df、stats、duration_ms 的结果字典
        """
        executor = RuleExecutor(self.rule_configs, self.lookup_tables)
        result_df, stats = executor.execute(self.df)
        duration_ms = int((time.time() - self._start_time) * 1000)
        return {
            "result_df": result_df,
            "stats": stats.to_dict(),
            "duration_ms": duration_ms,
        }

    def after(self, result: dict, **kwargs: Any) -> None:
        """后置处理 — 记录执行日志。"""
        result_df = result["result_df"]
        logger.info(
            f"DataFrame 转换完成: 输入 {len(self.df)} 行 → "
            f"输出 {len(result_df)} 行, 耗时 {result['duration_ms']}ms"
        )


# ───────────────────────── Command Pattern ─────────────────────────


class ExecuteDataFrameCommand:
    """执行 DataFrame 转换命令 — Command Pattern。

    将 DataFrame 执行操作封装为命令对象，支持通过 CommandInvoker 管理。
    execute() 返回协程，由调用方 await。

    Attributes:
        rule_configs: 规则配置列表
        lookup_tables: 映射表数据
        df: 输入 DataFrame
        source_name: 数据源名称
        task_repo: 任务仓储
    """

    def __init__(
        self,
        rule_configs: list[Any],
        lookup_tables: dict[str, dict],
        df: pl.DataFrame,
        source_name: str,
        task_repo: TaskRepository,
    ) -> None:
        self.rule_configs = rule_configs
        self.lookup_tables = lookup_tables
        self.df = df
        self.source_name = source_name
        self.task_repo = task_repo
        self._result: dict[str, Any] | None = None
        self._task: ExecutionTask | None = None

    async def execute(self) -> dict[str, Any]:
        """执行命令 — 模板方法转换 + 落库。

        Returns:
            执行结果摘要字典
        """
        input_rows = len(self.df)

        # Template Method: 同步转换部分
        template = DataFrameTransformTemplate(
            self.rule_configs, self.lookup_tables, self.df
        )
        transform_result = template.execute()
        result_df: pl.DataFrame = transform_result["result_df"]
        stats: dict = transform_result["stats"]
        duration_ms: int = transform_result["duration_ms"]

        # 落库记录
        task = ExecutionTask(
            task_name=self.source_name,
            status="completed",
            input_rows=input_rows,
            output_rows=len(result_df),
            stats=stats,
            duration_ms=duration_ms,
        )
        self._task = await self.task_repo.save(task)

        self._result = {
            "task_id": str(self._task.id),
            "status": "completed",
            "input_rows": input_rows,
            "output_rows": len(result_df),
            "error_rows": 0,
            "stats": stats,
            "duration_ms": duration_ms,
            "preview_rows": result_df.head(20).to_dicts(),
            "columns": result_df.columns,
        }
        return self._result

    async def undo(self) -> None:
        """撤销 — 删除已创建的任务记录。

        若命令尚未执行或任务已删除，则为 no-op。
        """
        if self._task is not None:
            try:
                # 标记为 cancelled 而非物理删除，保留审计痕迹
                self._task.status = "cancelled"
                await self.task_repo.save(self._task)
                logger.info(f"撤销执行任务: {self._task.id}")
            except Exception as e:
                logger.warning(f"撤销任务失败: {e}")


# ───────────────────────── Facade 服务 ─────────────────────────


class ExecutionService:
    """执行服务 — Template Method + Command Pattern。

    编排 DataFrame 规则执行的完整流程：
    1. 加载启用规则和映射表（异步 DB）
    2. 通过 DataFrameTransformTemplate 执行转换（模板方法）
    3. 通过 ExecuteDataFrameCommand 封装执行（命令模式）
    4. 落库记录并返回结果

    Attributes:
        rule_repo: 规则仓储
        lookup_table_repo: 映射表仓储
        task_repo: 任务仓储
        invoker: 命令调用器
    """

    def __init__(
        self,
        rule_repo: RuleRepository,
        lookup_table_repo: LookupTableRepository,
        task_repo: TaskRepository,
    ) -> None:
        self.rule_repo = rule_repo
        self.lookup_table_repo = lookup_table_repo
        self.task_repo = task_repo
        self.invoker = CommandInvoker()

    async def execute_dataframe(
        self,
        df: pl.DataFrame,
        source_name: str,
        *,
        _db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """对 DataFrame 跑全部启用规则，落 ExecutionTask，返回结果摘要。

        兼容旧 execute_dataframe 函数的完整签名和返回结构。

        Args:
            df: 输入 DataFrame
            source_name: 数据源名称（用于任务记录）
            _db: 废弃参数（规则和映射表通过 repo 加载），保留仅为向后兼容

        Returns:
            包含 task_id, status, input_rows, output_rows, stats,
            duration_ms, preview_rows, columns 的结果字典
        """
        start_time = time.time()
        input_rows = len(df)

        # 1. 加载启用规则
        rules = await self.rule_repo.find_all_enabled()
        rule_configs = [RuleParser.parse_rule(r) for r in rules]

        # 2. 加载映射表
        lookup_tables_list = await self.lookup_table_repo.find_all()
        lookup_tables = {str(t.id): t.data for t in lookup_tables_list}

        # 3. 构建并执行命令
        command = ExecuteDataFrameCommand(
            rule_configs=rule_configs,
            lookup_tables=lookup_tables,
            df=df,
            source_name=source_name,
            task_repo=self.task_repo,
        )
        # CommandInvoker.execute 是同步的，返回 command.execute() 的协程
        coroutine = command.execute()
        result = await coroutine

        logger.info(
            f"执行完成: {source_name}, 输入 {input_rows} 行, "
            f"耗时 {result['duration_ms']}ms"
        )
        return result

    async def execute_dataframe_with_invoker(
        self,
        df: pl.DataFrame,
        source_name: str,
        *,
        _db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """通过 CommandInvoker 执行 DataFrame 转换。

        与 execute_dataframe 功能相同，但通过 invoker 管理命令历史，
        支持 undo/redo。适用于需要撤销/重做的场景。

        Args:
            df: 输入 DataFrame
            source_name: 数据源名称
            _db: 废弃参数，保留仅为向后兼容

        Returns:
            执行结果摘要字典
        """
        rules = await self.rule_repo.find_all_enabled()
        rule_configs = [RuleParser.parse_rule(r) for r in rules]
        lookup_tables_list = await self.lookup_table_repo.find_all()
        lookup_tables = {str(t.id): t.data for t in lookup_tables_list}

        command = ExecuteDataFrameCommand(
            rule_configs=rule_configs,
            lookup_tables=lookup_tables,
            df=df,
            source_name=source_name,
            task_repo=self.task_repo,
        )
        # invoker.execute 返回协程，这里 await
        coroutine = self.invoker.execute(command)
        return await coroutine  # type: ignore[arg-type]
