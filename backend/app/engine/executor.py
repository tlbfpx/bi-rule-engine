"""规则执行器 — 核心引擎，对 DataFrame 执行规则转换。

RuleExecutor 只负责编排（拓扑排序、执行顺序），具体转换逻辑委托给
rule_handlers.RULE_HANDLER_REGISTRY 中的策略实现。

集成 Observer Pattern：可通过可选 event_bus 参数注入事件总线，
每条规则执行后发布 RuleExecutedEvent，全部完成后发布 ExecutionCompletedEvent。
"""
import time
import polars as pl
from loguru import logger

from app.engine.parser import RuleConfig
from app.engine.dependency import topological_sort
from app.engine.rule_handlers import RULE_HANDLER_REGISTRY
from app.patterns.observer import EventBus
from app.engine.observer import (
    RuleExecutedEvent,
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
)

# 进程级默认事件总线（单例），event_bus=None 时 executor 不发布事件；
# event_bus="default" 时使用该全局总线。
_default_event_bus: EventBus | None = None


def get_default_event_bus() -> EventBus:
    """获取进程级默认事件总线（惰性初始化的单例）"""
    global _default_event_bus
    if _default_event_bus is None:
        _default_event_bus = EventBus()
    return _default_event_bus


class RuleExecutionStats:
    """规则执行统计"""

    def __init__(self):
        self.field_stats: dict[str, dict] = {}

    def record(self, field: str, matched: int, defaulted: int, errors: int):
        self.field_stats[field] = {
            "matched": matched,
            "defaulted": defaulted,
            "errors": errors,
        }

    def to_dict(self) -> dict:
        return self.field_stats


class RuleExecutor:
    """规则执行器 — 编排层，不包含具体转换逻辑。

    所有转换策略通过 RULE_HANDLER_REGISTRY 注入，新增规则类型只需注册新 handler。
    """

    def __init__(self, rules: list[RuleConfig], lookup_tables: dict[str, dict] | None = None,
                 event_bus: EventBus | str | None = None):
        self.rules = [r for r in rules if r.enabled]
        self.lookup_tables = lookup_tables or {}
        self.stats = RuleExecutionStats()
        # event_bus 支持三种取值：
        #   None  → 不发布事件（保持原有静默行为）
        #   "default" → 使用进程级默认事件总线
        #   EventBus 实例 → 直接使用传入的总线
        if event_bus == "default":
            self.event_bus: EventBus | None = get_default_event_bus()
        else:
            self.event_bus = event_bus

    def execute(self, df: pl.DataFrame) -> tuple[pl.DataFrame, RuleExecutionStats]:
        """执行所有规则，按拓扑排序分层后逐条委托给对应的 RuleHandler"""
        _start_time = time.time()

        if not self.rules:
            logger.warning("没有启用的规则，返回原始数据")
            return df, self.stats

        try:
            levels = topological_sort(self.rules)
            logger.info(f"规则��行顺序: {len(levels)} 层, 共 {len(self.rules)} 条规则")
            for i, level in enumerate(levels):
                logger.info(f"  Level {i}: {[r.field_name for r in level]}")
        except Exception as e:
            logger.error(f"依赖分析失败: {e}")
            self._publish_execution_failed(error=str(e))
            raise

        df = df.with_columns(
            pl.lit(False).alias("_error_flag"),
            pl.lit("").alias("_error_msg"),
        )

        try:
            for level in levels:
                for rule in level:
                    df = self._execute_rule(df, rule)
        except Exception as e:
            logger.exception(f"规则执行过程异常: {e}")
            self._publish_execution_failed(error=str(e))
            raise

        # 清理执行器内部使用的辅助列，防止它们被写入目标表
        aux_cols = ["_error_flag", "_error_msg"]
        existing_aux = [c for c in aux_cols if c in df.columns]
        if existing_aux:
            df = df.drop(existing_aux)

        # 全部规则执行完毕后发布完成事件
        self._publish_execution_completed(df, _start_time)

        return df, self.stats

    def _execute_rule(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        """委托给注册的规则处理器 — 开闭原则：新增规则类型无需修改此方法"""
        logger.debug(f"执行规则: {rule.field_name} ({rule.rule_type})")

        handler = RULE_HANDLER_REGISTRY.get(rule.rule_type)
        if handler is None:
            logger.warning(f"未知规则类型: {rule.rule_type}")
            return df

        df = handler.execute(df, rule, self.lookup_tables, self.stats)

        # 规则执行后发布事件
        self._publish_rule_executed(rule)

        return df

    # ───────────────────────── 事件发布（Observer Pattern） ─────────────────────────

    def _publish_rule_executed(self, rule: RuleConfig) -> None:
        """发布单条规则执行完成事件（未注入 event_bus 时为空操作）"""
        if self.event_bus is None:
            return
        field_stat = self.stats.field_stats.get(rule.field_name, {})
        self.event_bus.publish(RuleExecutedEvent(
            name="rule_executed",
            rule_id=rule.rule_id,
            field_name=rule.field_name,
            rule_type=rule.rule_type,
            matched=field_stat.get("matched", 0),
            defaulted=field_stat.get("defaulted", 0),
            errors=field_stat.get("errors", 0),
        ))

    def _publish_execution_failed(self, error: str, rule_name: str = "", rule_type: str = "") -> None:
        """发布规则执行失败事件（未注入 event_bus 时为空操作）"""
        if self.event_bus is None:
            return
        self.event_bus.publish(ExecutionFailedEvent(
            name="execution_failed",
            error=error,
            rule_name=rule_name,
            rule_type=rule_type,
        ))

    def _publish_execution_completed(self, df: pl.DataFrame, start_time: float) -> None:
        """发布规则集执行完成事件（未注入 event_bus 时为空操作）"""
        if self.event_bus is None:
            return
        duration_ms = int((time.time() - start_time) * 1000)
        self.event_bus.publish(ExecutionCompletedEvent(
            name="execution_completed",
            total_rules=len(self.rules),
            total_rows=len(df),
            duration_ms=duration_ms,
            stats=self.stats.to_dict(),
        ))
