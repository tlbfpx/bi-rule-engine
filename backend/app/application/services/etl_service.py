"""ETL 编排服务 — Facade + Observer + State Machine + Template Method。

整合多种设计模式编排 ETL 任务执行：
- ETLPipelineTemplate: Template Method，封装 ETL 流水线（extract → transform → load）
- ETLService: Facade，对外暴露统一接口；内部使用 StateMachine 管理状态流转，
  通过 EventBus 发布生命周期事件

兼容性：旧 app/engine/etl_runner.py 的 run_etl_job 函数仍可直接使用，
ETLService 在其基础上增加状态机和事件通知能力。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from app.patterns.observer import Event, EventBus
from app.patterns.state_machine import State, StateMachine
from app.patterns.template import BaseTemplate

__all__ = [
    "ETLJobStartedEvent",
    "ETLJobCompletedEvent",
    "ETLJobFailedEvent",
    "ETLPipelineTemplate",
    "ETLService",
]


# ───────────────────────── ETL 事件定义 ─────────────────────────


@dataclass
class ETLJobStartedEvent(Event):
    """ETL 任务启动事件。

    Attributes:
        name: 事件名称（自动设置）
        job_id: ETL 任务 ID
        run_id: 执行记录 ID
    """

    name: str = "etl.job.started"
    job_id: str = ""
    run_id: str = ""


@dataclass
class ETLJobCompletedEvent(Event):
    """ETL 任务完成事件。

    Attributes:
        name: 事件名称（自动设置）
        job_id: ETL 任务 ID
        run_id: 执行记录 ID
        duration_ms: 执行耗时（毫秒）
        output_rows: 输出行数
    """

    name: str = "etl.job.completed"
    job_id: str = ""
    run_id: str = ""
    duration_ms: int = 0
    output_rows: int = 0


@dataclass
class ETLJobFailedEvent(Event):
    """ETL 任务失败事件。

    Attributes:
        name: 事件名称（自动设置）
        job_id: ETL 任务 ID
        run_id: 执行记录 ID
        error: 错误信息
    """

    name: str = "etl.job.failed"
    job_id: str = ""
    run_id: str = ""
    error: str = ""


# ───────────────────────── State Machine 状态 ─────────────────────────


class _PendingState(State):
    """待执行状态 — 初始状态。"""

    @property
    def name(self) -> str:
        return "pending"

    def on_enter(self, context: Any) -> None:
        logger.debug("ETL 状态 → pending")


class _RunningState(State):
    """执行中状态。"""

    @property
    def name(self) -> str:
        return "running"

    def on_enter(self, context: Any) -> None:
        logger.debug("ETL 状态 → running")


class _CompletedState(State):
    """已完成状态 — 终态。"""

    @property
    def name(self) -> str:
        return "completed"

    def on_enter(self, context: Any) -> None:
        logger.debug("ETL 状态 → completed")


class _FailedState(State):
    """失败状态 — 可通过 retry 回到 pending。"""

    @property
    def name(self) -> str:
        return "failed"

    def on_enter(self, context: Any) -> None:
        logger.debug("ETL 状态 → failed")


# ───────────────────────── Template Method ─────────────────────────


class ETLPipelineTemplate(BaseTemplate[dict]):
    """ETL 流水线模板方法 — extract → transform → load。

    同步执行 ETL 核心流程，异步 DB 操作由 ETLService 在调用前后处理。

    before() → 校验数据源和目标表配置
    do_execute() → extract → transform → load
    after() → 记录执行日志

    Attributes:
        data_source: 数据源 ORM 对象
        target: 目标表 ORM 对象
        run_id: 执行记录 ID
        rule_configs: 规则配置列表
        lookup_tables: 映射表数据字典
    """

    def __init__(
        self,
        data_source: Any,
        target: Any,
        run_id: str,
        rule_configs: list[Any],
        lookup_tables: dict[str, dict],
    ) -> None:
        self.data_source = data_source
        self.target = target
        self.run_id = run_id
        self.rule_configs = rule_configs
        self.lookup_tables = lookup_tables
        self._start_time: float = 0.0

    def before(self, **kwargs: Any) -> None:
        """前置校验 — 确保数据源和目标表配置完整。"""
        self._start_time = time.time()
        if self.data_source is None:
            raise ValueError("数据源不能为空")
        if self.target is None:
            raise ValueError("目标表不能为空")
        logger.info(
            f"ETL 流水线准备: job_source={self.data_source.name}, "
            f"target={self.target.table_name}, run_id={self.run_id}"
        )

    def do_execute(self, **kwargs: Any) -> dict[str, Any]:
        """核心逻辑 — extract → transform → load。

        委托给 etl_runner 的同步函数，避免重复实现。

        Returns:
            ETL 执行结果字典，包含 status, input_rows, output_rows,
            duration_ms, stats, error_log 等字段
        """
        from app.engine.etl_runner import _sync_etl_core

        result = _sync_etl_core(
            data_source=self.data_source,
            target=self.target,
            run_id=self.run_id,
            rule_configs=self.rule_configs,
            lookup_tables=self.lookup_tables,
        )
        return result

    def after(self, result: dict, **kwargs: Any) -> None:
        """后置处理 — 记录执行结果日志。"""
        status = result.get("status", "unknown")
        duration = result.get("duration_ms", 0)
        input_rows = result.get("input_rows", 0)
        output_rows = result.get("output_rows", 0)
        logger.info(
            f"ETL 流水线完成: status={status}, "
            f"input={input_rows}, output={output_rows}, "
            f"duration={duration}ms"
        )


# ───────────────────────── Facade 服务 ─────────────────────────


class ETLService:
    """ETL 任务编排服务 — Facade + Observer + StateMachine。

    整合状态机管理状态流转、事件总线发布生命周期事件、模板方法执行流水线。

    状态流转：PENDING →(start)→ RUNNING →(complete)→ COMPLETED
                                            →(fail)→ FAILED →(retry)→ PENDING

    Attributes:
        event_bus: 事件总线实例
    """

    # 类级状态机配置缓存：状态定义和转换规则是固定的，只需构建一次
    _sm_transitions: list[tuple[str, str, str]] | None = None
    _sm_states: list[State] | None = None

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        # 首次实例化时构建共享配置
        if ETLService._sm_transitions is None:
            ETLService._sm_states = [
                _PendingState(), _RunningState(),
                _CompletedState(), _FailedState(),
            ]
            ETLService._sm_transitions = [
                ("pending", "running", "start"),
                ("running", "completed", "complete"),
                ("running", "failed", "fail"),
                ("failed", "pending", "retry"),
            ]

    def _build_state_machine(self) -> StateMachine:
        """构建 ETL Job 状态机。

        状态定义和转换规则从类级缓存读取，避免每次执行重复构建。
        每次返回新的 StateMachine 实例（状态是执行隔离的）。

        Returns:
            配置好的 StateMachine 实例，初始状态为 pending
        """
        sm = StateMachine()
        assert ETLService._sm_states is not None
        assert ETLService._sm_transitions is not None
        for state in ETLService._sm_states:
            sm.add_state(state)
        for from_state, to_state, event in ETLService._sm_transitions:
            sm.add_transition(from_state, to_state, event)
        return sm

    async def execute_job(
        self,
        job_id: str,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """执行 ETL 任务 — 完整的状态机 + 事件驱动流程。

        流程：
        1. 创建状态机（PENDING）
        2. 状态转换 PENDING→RUNNING，发布 JobStartedEvent
        3. 加载任务配置、规则、映射表
        4. 通过 ETLPipelineTemplate 执行 ETL 流水线
        5. 成功：状态转换 RUNNING→COMPLETED，发布 JobCompletedEvent
           失败：状态转换 RUNNING→FAILED，发布 JobFailedEvent
        6. 更新执行记录和任务状态

        Args:
            job_id: ETL 任务 ID
            run_id: 可选的执行记录 ID（None 则自动创建）
            trace_id: 可选的链路追踪 ID

        Returns:
            执行结果摘要字典
        """
        # 延迟导入避免循环依赖
        from app.db import AsyncSessionLocal
        from app.engine.etl_runner import (
            _get_executed_sql_for_log,
            _load_rules_and_lookup,
        )
        from app.logging import generate_trace_id, get_trace_id, set_trace_id
        from app.models.etl_job import ETLJob
        from app.models.etl_job_run import ETLJobRun
        from sqlalchemy import select

        start_time = time.time()

        # 设置 trace_id
        if trace_id:
            set_trace_id(trace_id)
        else:
            current = get_trace_id()
            if not current:
                set_trace_id(generate_trace_id())

        # 1. 构建状态机
        sm = self._build_state_machine()
        logger.info(f"ETL 任务开始: job={job_id}, run={run_id}")

        # 2. 加载任务配置 & 创建执行记录
        async with AsyncSessionLocal() as session:
            job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if not job:
                raise ValueError(f"ETL 任务不存在: {job_id}")

            data_source = job.data_source
            target = job.target_table

            if run_id is None:
                run_record = ETLJobRun(
                    etl_job_id=job_id,
                    status="pending",
                    trace_id=get_trace_id(),
                )
                session.add(run_record)
                await session.flush()
                await session.refresh(run_record)
                run_id = str(run_record.id)
            else:
                run_result = await session.execute(
                    select(ETLJobRun).where(ETLJobRun.id == run_id)
                )
                run_record = run_result.scalar_one_or_none()
                if not run_record:
                    raise ValueError(f"执行记录不存在: {run_id}")

            # 3. 状态转换 PENDING→RUNNING
            sm.trigger("start")
            run_record.status = "running"
            run_record.started_at = datetime.now()
            await session.commit()

            # 4. 发布 JobStartedEvent
            self.event_bus.publish(ETLJobStartedEvent(
                job_id=job_id,
                run_id=run_id,
            ))

            # 5. 加载规则和映射表
            rule_configs, lookup_tables = await _load_rules_and_lookup(
                session, job.rule_set_id
            )

        # 6. 执行 ETL 流水线（模板方法）
        try:
            import asyncio

            pipeline = ETLPipelineTemplate(
                data_source=data_source,
                target=target,
                run_id=run_id,
                rule_configs=rule_configs,
                lookup_tables=lookup_tables,
            )
            # 同步 ETL 核心在线程中执行，避免阻塞事件循环
            core_result = await asyncio.to_thread(pipeline.execute)

        except Exception as e:
            logger.exception(f"ETL 执行失败 [job={job_id}, run={run_id}]")
            # 7b. 失败：状态转换 RUNNING→FAILED
            sm.trigger("fail")

            error_msg = str(e)
            self.event_bus.publish(ETLJobFailedEvent(
                job_id=job_id,
                run_id=run_id,
                error=error_msg,
            ))

            # 更新执行记录
            async with AsyncSessionLocal() as session:
                run_result = await session.execute(
                    select(ETLJobRun).where(ETLJobRun.id == run_id)
                )
                run_record = run_result.scalar_one_or_none()
                if run_record:
                    run_record.status = "failed"
                    run_record.completed_at = datetime.now()
                    run_record.duration_ms = int((time.time() - start_time) * 1000)
                    run_record.error_log = {
                        "message": error_msg,
                        "exception": type(e).__name__,
                    }
                    run_record.executed_sql = _get_executed_sql_for_log(data_source)

                job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.last_run_at = datetime.now()
                    job.last_run_status = "failed"
                    job.last_run_error = error_msg

                await session.commit()

            return {
                "status": "failed",
                "input_rows": 0,
                "output_rows": 0,
                "error_rows": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "run_id": run_id,
                "error": error_msg,
            }

        # 7a. 成功：状态转换 RUNNING→COMPLETED
        sm.trigger("complete")

        duration_ms = core_result.get("duration_ms", int((time.time() - start_time) * 1000))
        output_rows = core_result.get("output_rows", 0)

        self.event_bus.publish(ETLJobCompletedEvent(
            job_id=job_id,
            run_id=run_id,
            duration_ms=duration_ms,
            output_rows=output_rows,
        ))

        # 8. 更新执行记录和任务状态
        async with AsyncSessionLocal() as session:
            run_result = await session.execute(
                select(ETLJobRun).where(ETLJobRun.id == run_id)
            )
            run_record = run_result.scalar_one_or_none()
            if run_record:
                run_record.status = core_result["status"]
                run_record.completed_at = datetime.now()
                run_record.duration_ms = core_result["duration_ms"]
                run_record.input_rows = core_result["input_rows"]
                run_record.output_rows = core_result["output_rows"]
                run_record.error_rows = core_result["error_rows"]
                run_record.executed_sql = core_result["executed_sql"]
                run_record.stats = core_result["stats"]
                run_record.error_log = core_result["error_log"]

            job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if job:
                job.last_run_at = datetime.now()
                job.last_run_status = core_result["status"]
                job.last_run_error = core_result["error_log"].get("message")

            # 更新增量值
            if core_result.get("incremental_value"):
                from app.models.data_source import DataSource
                ds_result = await session.execute(
                    select(DataSource).where(DataSource.id == data_source.id)
                )
                ds = ds_result.scalar_one_or_none()
                if ds:
                    ds.incremental_value = core_result["incremental_value"]

            await session.commit()

        return {
            "status": core_result["status"],
            "input_rows": core_result["input_rows"],
            "output_rows": core_result["output_rows"],
            "error_rows": core_result["error_rows"],
            "duration_ms": core_result["duration_ms"],
            "run_id": run_id,
        }
