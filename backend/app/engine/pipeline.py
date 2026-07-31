"""规则执行管道 — Chain of Responsibility + Template Method。

- RuleExecutionPipeline 基于 BaseTemplate（Template Method）：
  before() 验证/拓扑排序 → do_execute() 逐层执行 → after() 统计/审计。
- PreExecutionValidator / PostExecutionAuditor 基于 HandlerChain（责任链），
  可在管道前后插入任意处理器，新增处理器无需修改管道本身。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import polars as pl
from loguru import logger

from app.patterns.template import BaseTemplate
from app.patterns.chain import HandlerChain, IHandler
from app.patterns.observer import EventBus
from app.engine.parser import RuleConfig
from app.engine.dependency import topological_sort
from app.engine.executor import RuleExecutor, RuleExecutionStats
from app.engine.observer import ExecutionCompletedEvent


@dataclass
class RuleExecutionContext:
    """规则执行上下文 — 在管道与责任链处理器之间传递"""

    df: pl.DataFrame
    rule_configs: list[RuleConfig]
    lookup_tables: dict[str, dict] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    levels: list[list[RuleConfig]] | None = None
    result_df: pl.DataFrame | None = None


class PreExecutionValidator(IHandler[RuleExecutionContext]):
    """前置校验器 — 校验上下文合法性（空规则、依赖成环等）

    返回 False 将终止责任链（阻断后续处理器）。
    """

    def handle(self, context: RuleExecutionContext) -> bool:
        if not context.rule_configs:
            logger.warning("PreExecutionValidator: 没有规则配置，跳过后续处理器")
            return False
        enabled = [r for r in context.rule_configs if r.enabled]
        if not enabled:
            logger.warning("PreExecutionValidator: 没有启用的规则")
            return False
        try:
            context.levels = topological_sort(enabled)
        except Exception as e:
            logger.error(f"PreExecutionValidator: 依赖分析失败: {e}")
            raise
        logger.info(
            f"PreExecutionValidator: 校验通过, {len(context.levels)} 层 / {len(enabled)} 条规则"
        )
        return True


class PostExecutionAuditor(IHandler[RuleExecutionContext]):
    """后置审计器 — 记录执行结果统计日志"""

    def handle(self, context: RuleExecutionContext) -> bool:
        if context.result_df is not None:
            logger.info(
                f"PostExecutionAuditor: 输入 {len(context.df)} 行 -> 输出 {len(context.result_df)} 行, "
                f"字段统计 {len(context.stats)} 项"
            )
        return True


class RuleExecutionPipeline(BaseTemplate[pl.DataFrame]):
    """规则执行管道 — Template Method Pattern

    - before(): 执行前置责任链（验证 + 拓扑排序）
    - do_execute(): 委托 RuleExecutor 按拓扑顺序执行各级规则
    - after(): 执行后置责任链（日志/统计），发布 ExecutionCompletedEvent

    构造器参数均可选注入，默认行为与直接调用 RuleExecutor 等价。
    """

    def __init__(
        self,
        executor: RuleExecutor | None = None,
        pre_chain: HandlerChain[RuleExecutionContext] | None = None,
        post_chain: HandlerChain[RuleExecutionContext] | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._executor = executor
        self._event_bus = event_bus
        self._pre_chain = pre_chain or HandlerChain[RuleExecutionContext]()
        self._post_chain = post_chain or HandlerChain[RuleExecutionContext]()
        # 默认责任链：前置校验 + 后置审计
        if pre_chain is None:
            self._pre_chain.add_handler(PreExecutionValidator())
        if post_chain is None:
            self._post_chain.add_handler(PostExecutionAuditor())
        self._start_time: float = 0.0
        self._stats: RuleExecutionStats | None = None

    def before(self, **kwargs: Any) -> None:
        """前置钩子 — 运行前置责任链（验证/排序）"""
        context: RuleExecutionContext = kwargs["context"]
        self._start_time = time.time()
        self._pre_chain.execute(context)

    def do_execute(self, **kwargs: Any) -> pl.DataFrame:
        """核心逻辑 — 委托 RuleExecutor 执行规则"""
        context: RuleExecutionContext = kwargs["context"]
        executor = self._executor or RuleExecutor(
            context.rule_configs, context.lookup_tables, event_bus=self._event_bus
        )
        result_df, stats = executor.execute(context.df)
        context.result_df = result_df
        context.stats = stats.to_dict()
        self._stats = stats
        return result_df

    def after(self, result: pl.DataFrame, **kwargs: Any) -> None:
        """后置钩子 — 运行后置责任链（日志/统计），发布完成事件"""
        context: RuleExecutionContext = kwargs["context"]
        self._post_chain.execute(context)
        if self._event_bus is not None:
            duration_ms = int((time.time() - self._start_time) * 1000)
            enabled = [r for r in context.rule_configs if r.enabled]
            self._event_bus.publish(ExecutionCompletedEvent(
                name="execution_completed",
                total_rules=len(enabled),
                total_rows=len(result),
                duration_ms=duration_ms,
                stats=context.stats,
            ))
