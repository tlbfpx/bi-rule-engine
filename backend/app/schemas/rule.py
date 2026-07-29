"""规则 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional


class ConditionRowSchema(BaseModel):
    id: str
    field: str
    operator: str
    value: Any = None


class ConditionGroupSchema(BaseModel):
    id: str
    priority: int = 1
    logic: str = "AND"
    rows: list[ConditionRowSchema] = []
    result_type: str = "constant"
    result_value: Any = None


class RuleConfigSchema(BaseModel):
    conditions: list[ConditionGroupSchema] = []
    cleaning_steps: list[dict] = []
    lookup_table_id: Optional[str] = None
    lookup_key_field: Optional[str] = None
    lookup_value_field: Optional[str] = None
    lookup_fallbacks: list[dict] = []
    formula_expression: Optional[str] = None
    default_result: Any = None


class RuleCreate(BaseModel):
    rule_set_id: Optional[str] = None
    field_name: str = Field(..., max_length=100)
    field_label: Optional[str] = None
    rule_type: str = Field(..., pattern="^(mapping|cleaning|lookup|computed)$")
    priority: int = 0
    enabled: bool = True
    config: RuleConfigSchema = Field(default_factory=RuleConfigSchema)
    lookup_table_id: Optional[str] = None
    depends_on: list[str] = []
    description: Optional[str] = None


class RuleUpdate(BaseModel):
    rule_set_id: Optional[str] = None
    field_label: Optional[str] = None
    rule_type: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[RuleConfigSchema] = None
    lookup_table_id: Optional[str] = None
    depends_on: Optional[list[str]] = None
    description: Optional[str] = None


class RuleTestRequest(BaseModel):
    test_rows: list[dict]


class BatchPriorityUpdate(BaseModel):
    items: list[dict]


class RuleOut(BaseModel):
    """规则响应。config 等半结构化字段用宽松类型，避免深度校验触发 500。"""
    id: str
    rule_set_id: Optional[str] = None
    field_name: str
    field_label: Optional[str] = None
    rule_type: str
    priority: int
    enabled: bool
    config: dict = Field(default_factory=dict)
    lookup_table_id: Optional[str] = None
    depends_on: list = Field(default_factory=list)
    description: Optional[str] = None
    created_by: Optional[str] = None
    rule_set_name: Optional[str] = None  # 仅 list 端点由路由注入
    created_at: datetime
    updated_at: datetime
