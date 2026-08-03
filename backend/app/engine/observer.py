"""引擎事件系统 — Observer Pattern。

定义规则执行生命周期事件，并提供开箱即用的监听器实现。
事件通过 EventBus（单例）发布/订阅，与执行器解耦。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.patterns.observer import Event, EventBus


@dataclass
class RuleExecutedEvent(Event):
    """单条规则执行完成事件"""

    rule_id: str = ""
    field_name: str = ""
    rule_type: str = ""
    matched: int = 0
    defaulted: int = 0
    errors: int = 0


@dataclass
class ExecutionCompletedEvent(Event):
    """整个规则集执行完成事件"""

    total_rules: int = 0
    total_rows: int = 0
    duration_ms: int = 0
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionFailedEvent(Event):
    """规则执行失败事件 — 单条规则或整个规则集执行抛异常时发布"""

    error: str = ""
    rule_name: str = ""
    rule_type: str = ""


# ───────────────────────── ETL 阶段进度事件 ─────────────────────────


@dataclass
class ETLProgressEvent(Event):
    """ETL 执行阶段进度事件

    用于 WebSocket 进度推送，携带 run_id 以便 ConnectionManager 路由到正确订阅者。
    """

    run_id: str = ""
    job_id: str = ""
    phase: str = ""       # extracting / transforming / loading / completed / failed
    message: str = ""
    input_rows: int = 0
    output_rows: int = 0
    progress: float = 0.0  # 0.0 ~ 1.0


class RuleExecutionListener:
    """规则执行监听器 — 记录每次规则执行统计"""

    def __init__(self) -> None:
        self.rule_events: list[RuleExecutedEvent] = []
        self.completed_events: list[ExecutionCompletedEvent] = []
        self.failed_events: list[ExecutionFailedEvent] = []

    def on_event(self, event: Event) -> None:
        """处理事件 — 按事件类型分发记录"""
        if isinstance(event, RuleExecutedEvent):
            self.rule_events.append(event)
            logger.debug(
                f"[事件] 规则执行完成: {event.field_name} ({event.rule_type}) "
                f"matched={event.matched} defaulted={event.defaulted} errors={event.errors}"
            )
        elif isinstance(event, ExecutionCompletedEvent):
            self.completed_events.append(event)
            logger.info(
                f"[事件] 规则集执行完成: {event.total_rules} 条规则, "
                f"{event.total_rows} 行, 耗时 {event.duration_ms}ms"
            )
        elif isinstance(event, ExecutionFailedEvent):
            self.failed_events.append(event)
            logger.error(
                f"[事件] 规则执行失败: {event.rule_name} ({event.rule_type}) - {event.error}"
            )
        else:
            logger.debug(f"[事件] 未处理的事件类型: {event.name}")

    def subscribe(self, event_bus: EventBus | None = None) -> "RuleExecutionListener":
        """订阅规则执行相关事件，返回 self 支持链式调用"""
        bus = event_bus or EventBus()
        bus.subscribe("rule_executed", self)
        bus.subscribe("execution_completed", self)
        bus.subscribe("execution_failed", self)
        return self
