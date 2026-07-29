"""任务 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class TaskCreate(BaseModel):
    task_name: Optional[str] = None
    source_id: Optional[str] = None
    template_id: Optional[str] = None
    query_params: dict = Field(default_factory=dict)
    output_format: str = "xlsx"


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
