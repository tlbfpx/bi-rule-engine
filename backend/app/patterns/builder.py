"""Builder Pattern — 建造者基础设施

提供建造者接口与规则配置链式建造者。
"""
from __future__ import annotations

from typing import Any, Protocol

from app.engine.parser import RuleConfig


class IBuilder[T](Protocol):
    """建造者接口"""

    def build(self) -> T:
        """构建目标对象"""
        ...


class RuleConfigBuilder:
    """规则配置建造者 — 链式调用构建 RuleConfig"""

    def __init__(self) -> None:
        self._rule_id: str = ""
        self._rule_type: str = ""
        self._field_name: str = ""
        self._field_label: str = ""
        self._conditions: list[Any] = []
        self._cleaning_steps: list[dict] = []
        self._formula_expression: str | None = None
        self._depends_on: list[str] = []
        self._default_result: Any = None

    def with_id(self, rule_id: str) -> RuleConfigBuilder:
        """设置规则 ID"""
        self._rule_id = rule_id
        return self

    def with_type(self, rule_type: str) -> RuleConfigBuilder:
        """设置规则类型"""
        self._rule_type = rule_type
        return self

    def with_field(self, name: str, label: str) -> RuleConfigBuilder:
        """设置字段名与标签"""
        self._field_name = name
        self._field_label = label
        return self

    def with_conditions(self, conditions: list[Any]) -> RuleConfigBuilder:
        """设置条件组"""
        self._conditions = conditions
        return self

    def with_cleaning_steps(self, steps: list[dict]) -> RuleConfigBuilder:
        """设置清洗步骤"""
        self._cleaning_steps = steps
        return self

    def with_formula(self, expression: str) -> RuleConfigBuilder:
        """设置公式表达式"""
        self._formula_expression = expression
        return self

    def with_dependencies(self, deps: list[str]) -> RuleConfigBuilder:
        """设置依赖规则"""
        self._depends_on = deps
        return self

    def with_default_result(self, value: Any) -> RuleConfigBuilder:
        """设置默认结果"""
        self._default_result = value
        return self

    def build(self) -> RuleConfig:
        """构建 RuleConfig 实例"""
        return RuleConfig(
            rule_id=self._rule_id,
            field_name=self._field_name,
            field_label=self._field_label,
            rule_type=self._rule_type,
            priority=0,
            enabled=True,
            conditions=self._conditions,
            cleaning_steps=self._cleaning_steps,
            formula_expression=self._formula_expression,
            default_result=self._default_result,
            depends_on=self._depends_on,
        )
