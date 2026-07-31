"""映射表 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.utils.sanitize import sanitize_user_input


class LookupTableCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    source_type: str = "upload"
    columns: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)

    @field_validator("data", mode="before")
    @classmethod
    def sanitize_data_values(cls, v):
        """递归清理查找表数据中的字符串值"""
        if isinstance(v, dict):
            return {
                sanitize_user_input(str(k)) if isinstance(k, str) else k:
                sanitize_user_input(str(val)) if isinstance(val, str) else val
                for k, val in v.items()
            }
        return v


class LookupTableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[dict] = None
    data: Optional[dict] = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)

    @field_validator("data", mode="before")
    @classmethod
    def sanitize_data_values(cls, v):
        if isinstance(v, dict):
            return {
                sanitize_user_input(str(k)) if isinstance(k, str) else k:
                sanitize_user_input(str(val)) if isinstance(val, str) else val
                for k, val in v.items()
            }
        return v


class LookupTableOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    columns: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    row_count: int = 0
    created_at: datetime
    updated_at: datetime
