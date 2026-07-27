"""规则 DSL 解析器 — 将 JSON 条件配置解析为可执行操作"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConditionRow:
    """单个条件行"""
    field: str
    operator: str
    value: Any = None


@dataclass
class ConditionGroup:
    """条件组 — 多个条件行用 AND/OR 组合"""
    id: str
    priority: int
    logic: str = "AND"
    rows: list[ConditionRow] = field(default_factory=list)
    result_type: str = "constant"
    result_value: Any = None


@dataclass
class RuleConfig:
    """解析后的规则配置"""
    rule_id: str
    field_name: str
    field_label: str
    rule_type: str
    priority: int
    enabled: bool
    conditions: list[ConditionGroup] = field(default_factory=list)
    cleaning_steps: list[dict] = field(default_factory=list)
    lookup_table_id: str | None = None
    lookup_key_field: str | None = None
    lookup_value_field: str | None = None
    lookup_fallbacks: list[dict] = field(default_factory=list)
    formula_expression: str | None = None
    default_result: Any = None
    depends_on: list[str] = field(default_factory=list)
    description: str = ""


class RuleParser:
    """将数据库中的 JSON 规则配置解析为 RuleConfig 对象"""

    @staticmethod
    def parse(rule_dict: dict) -> RuleConfig:
        config = rule_dict.get("config", {})

        conditions = []
        for cg in config.get("conditions", []):
            rows = [
                ConditionRow(
                    field=r["field"],
                    operator=r["operator"],
                    value=r.get("value"),
                )
                for r in cg.get("rows", [])
            ]
            conditions.append(ConditionGroup(
                id=cg.get("id", ""),
                priority=cg.get("priority", 0),
                logic=cg.get("logic", "AND"),
                rows=rows,
                result_type=cg.get("result_type", "constant"),
                result_value=cg.get("result_value"),
            ))

        return RuleConfig(
            rule_id=rule_dict.get("rule_id", ""),
            field_name=rule_dict["field_name"],
            field_label=rule_dict.get("field_label", ""),
            rule_type=rule_dict["rule_type"],
            priority=rule_dict.get("priority", 0),
            enabled=rule_dict.get("enabled", True),
            conditions=conditions,
            cleaning_steps=config.get("cleaning_steps", []),
            lookup_table_id=config.get("lookup_table_id"),
            lookup_key_field=config.get("lookup_key_field"),
            lookup_value_field=config.get("lookup_value_field"),
            lookup_fallbacks=config.get("lookup_fallbacks", []),
            formula_expression=config.get("formula_expression"),
            default_result=config.get("default_result"),
            depends_on=rule_dict.get("depends_on", []),
            description=rule_dict.get("description", ""),
        )
