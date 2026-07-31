"""规则 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional
from app.utils.sanitize import sanitize_user_input


class ConditionRowSchema(BaseModel):
    id: str = Field(..., max_length=64)
    field: str = Field(..., max_length=100)
    operator: str = Field(..., pattern=r"^(eq|ne|gt|gte|lt|lte|contains|not_contains|starts_with|ends_with|in|not_in|is_null|is_not_null|matches|not_matches)$")
    value: Any = None

    @field_validator("value", mode="before")
    @classmethod
    def sanitize_value(cls, v):
        """清理条件值中的 XSS payload（仅针对字符串类型）"""
        if isinstance(v, str):
            return sanitize_user_input(v)
        return v


class ConditionGroupSchema(BaseModel):
    id: str = Field(..., max_length=64)
    priority: int = Field(default=1, ge=0, le=9999)
    logic: str = Field(default="AND", pattern="^(AND|OR)$")
    rows: list[ConditionRowSchema] = []
    result_type: str = Field(default="constant", pattern="^(constant|field_value)$")
    result_value: Any = None

    @field_validator("result_value", mode="before")
    @classmethod
    def sanitize_result_value(cls, v):
        """清理结果值中的 XSS payload"""
        if isinstance(v, str):
            return sanitize_user_input(v)
        return v


class RuleConfigSchema(BaseModel):
    conditions: list[ConditionGroupSchema] = []
    cleaning_steps: list[dict] = []
    lookup_table_id: Optional[str] = None
    lookup_key_field: Optional[str] = None
    lookup_value_field: Optional[str] = None
    lookup_fallbacks: list[dict] = []
    formula_expression: Optional[str] = None
    default_result: Any = None

    @field_validator("formula_expression", mode="before")
    @classmethod
    def sanitize_formula(cls, v):
        return sanitize_user_input(v)


class RuleCreate(BaseModel):
    rule_set_id: Optional[str] = None
    field_name: str = Field(..., max_length=100)
    field_label: Optional[str] = None
    rule_type: str = Field(..., pattern="^(mapping|cleaning|lookup|computed)$")
    priority: int = Field(default=0, ge=-9999, le=9999)
    enabled: bool = True
    config: RuleConfigSchema = Field(default_factory=RuleConfigSchema)
    lookup_table_id: Optional[str] = None
    depends_on: list[str] = []
    description: Optional[str] = None

    @field_validator("field_name", "field_label", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


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

    @field_validator("field_label", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class RuleTestRequest(BaseModel):
    test_rows: list[dict] = Field(..., max_length=500)


class BatchPriorityItem(BaseModel):
    id: str = Field(..., max_length=36)
    priority: int = Field(..., ge=-9999, le=9999)


class BatchPriorityUpdate(BaseModel):
    items: list[BatchPriorityItem] = Field(..., max_length=500)


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
