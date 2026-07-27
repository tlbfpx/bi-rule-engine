"""任务 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional


class TaskCreate(BaseModel):
    task_name: Optional[str] = None
    source_id: Optional[str] = None
    template_id: Optional[str] = None
    query_params: dict = Field(default_factory=dict)
    output_format: str = "xlsx"
