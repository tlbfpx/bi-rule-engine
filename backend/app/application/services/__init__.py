"""应用服务层 — 导出所有应用服务类。

应用服务封装业务用例，通过 Repository 接口访问数据，
不直接操作 HTTP 请求/响应（阿里规约）。

设计模式：
- RuleService: Facade — 规则管理
- ExecutionService: Template Method + Command — DataFrame 执行
- ETLService: Facade + Observer + StateMachine — ETL 编排
- ValidationChain: Chain of Responsibility — 输入校验
"""
from __future__ import annotations

from app.application.services.etl_service import (
    ETLJobCompletedEvent,
    ETLJobFailedEvent,
    ETLJobStartedEvent,
    ETLPipelineTemplate,
    ETLService,
)
from app.application.services.execution_service import (
    DataFrameTransformTemplate,
    ExecuteDataFrameCommand,
    ExecutionService,
    LookupTableRepository,
    RuleRepository,
    TaskRepository,
)
from app.application.services.rule_service import (
    RuleRepository as AppRuleRepository,
    RuleService,
)
from app.application.services.validation_service import (
    ConditionValidator,
    FieldNameValidator,
    RuleTypeValidator,
    ValidationChain,
    ValidationContext,
    ValidationResult,
)

__all__ = [
    # Rule Service
    "RuleService",
    "AppRuleRepository",
    # Execution Service
    "ExecutionService",
    "DataFrameTransformTemplate",
    "ExecuteDataFrameCommand",
    "RuleRepository",
    "LookupTableRepository",
    "TaskRepository",
    # ETL Service
    "ETLService",
    "ETLPipelineTemplate",
    "ETLJobStartedEvent",
    "ETLJobCompletedEvent",
    "ETLJobFailedEvent",
    # Validation Service
    "ValidationChain",
    "ValidationContext",
    "ValidationResult",
    "RuleTypeValidator",
    "FieldNameValidator",
    "ConditionValidator",
]
