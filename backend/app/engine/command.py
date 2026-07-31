"""ETL 命令封装 — Command Pattern。

将 ETL 三个阶段（抽取/转换/加载）封装为命令对象，
配合 CommandInvoker 可维护命令历史、支持撤销与重做。
各命令内部复用 etl_runner 中的同步执行函数，不重复实现逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import polars as pl
from loguru import logger

from app.patterns.command import ICommand
from app.engine.parser import RuleConfig
from app.engine.etl_runner import (
    _read_source_sync,
    _execute_transform_sync,
    _write_to_target,
)


@dataclass
class ExtractCommand(ICommand):
    """数据抽取命令 — 从数据源读取 DataFrame

    undo 为 no-op（抽取是无副作用的读操作），返回缓存的 DataFrame 引用数。
    """

    data_source: Any
    _result: pl.DataFrame | None = field(default=None, init=False, repr=False)

    def execute(self) -> pl.DataFrame:
        """执行抽取，结果缓存在命令实例上供后续命令/撤销使用"""
        self._result = _read_source_sync(self.data_source)
        return self._result

    def undo(self) -> None:
        """撤销 — 抽取无副作用，仅释放缓存引用"""
        logger.info("ExtractCommand.undo: 释放缓存的抽取结果")
        self._result = None
        return None


@dataclass
class TransformCommand(ICommand):
    """数据转换命令 — 对 DataFrame 执行规则引擎

    undo 返回转换前的原始 DataFrame（转换是纯函数，无需回滚外部状态）。
    """

    df: pl.DataFrame
    rule_configs: list[RuleConfig]
    lookup_tables: dict[str, dict]
    _result: tuple[pl.DataFrame, dict] | None = field(default=None, init=False, repr=False)

    def execute(self) -> tuple[pl.DataFrame, dict]:
        """执行转换，返回 (结果 DataFrame, 统计字典)"""
        self._result = _execute_transform_sync(self.df, self.lookup_tables, self.rule_configs)
        return self._result

    def undo(self) -> pl.DataFrame:
        """撤销 — 返回转换前的原始 DataFrame"""
        logger.info("TransformCommand.undo: 返回转换前的原始 DataFrame")
        return self.df


@dataclass
class LoadCommand(ICommand):
    """数据加载命令 — 将 DataFrame 写入目标表

    undo 无法物理删除已写入行（数据库不具备通用回滚语义），
    返回已写入行数并记录告警日志，由调用方决定补偿策略。
    """

    df: pl.DataFrame
    target: Any
    run_id: str
    _written_rows: int = field(default=0, init=False, repr=False)

    def execute(self) -> int:
        """执行加载，返回写入行数"""
        self._written_rows = _write_to_target(self.df, self.target, self.run_id)
        return self._written_rows

    def undo(self) -> int:
        """撤销 — 返回已写入行数（物理回滚由调用方按 run_id 补偿）"""
        logger.warning(
            f"LoadCommand.undo: 已写入 {self._written_rows} 行 (run_id={self.run_id}), "
            "物理回滚需按 run_id 执行补偿删除"
        )
        return self._written_rows
