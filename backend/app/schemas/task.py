"""任务 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.utils.sanitize import sanitize_user_input


class TaskCreate(BaseModel):
    task_name: Optional[str] = Field(default=None, max_length=200)
    source_id: Optional[str] = Field(default=None, max_length=100)
    template_id: Optional[str] = Field(default=None, max_length=100)
    query_params: dict = Field(default_factory=dict)
    output_format: str = Field(default="xlsx", pattern="^(xlsx|csv)$")

    @field_validator("task_name", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class TaskOut(BaseModel):
    """ExecutionTask 响应（不含 error_log 列）。"""
    id: str
    task_name: Optional[str] = None
    source_id: Optional[str] = None
    template_id: Optional[str] = None
    query_params: dict = Field(default_factory=dict)
    status: str
    output_format: str = "xlsx"
    output_file: Optional[str] = None
    input_rows: Optional[int] = None
    output_rows: Optional[int] = None
    error_rows: int = 0
    stats: dict = Field(default_factory=dict)
    duration_ms: Optional[int] = None
    created_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
