"""ETL 调度任务 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.schemas.data_source import DataSourceOut
from app.schemas.target_table import TargetTableOut
from app.utils.sanitize import sanitize_user_input


class ETLJobBase(BaseModel):
    job_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    data_source_id: str
    target_table_id: str
    rule_set_id: Optional[str] = None
    cron_expression: str = Field(..., max_length=100)
    timezone: str = Field(default="Asia/Shanghai", max_length=50)
    error_retry_count: int = Field(default=0, ge=0, le=10)
    timeout_seconds: int = Field(default=3600, ge=60, le=86400)


class ETLJobCreate(ETLJobBase):
    @field_validator("job_name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class ETLJobUpdate(BaseModel):
    job_name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    data_source_id: Optional[str] = None
    target_table_id: Optional[str] = None
    rule_set_id: Optional[str] = None
    cron_expression: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    error_retry_count: Optional[int] = Field(default=None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(default=None, ge=60, le=86400)

    @field_validator("job_name", "description", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        return sanitize_user_input(v)


class ETLJobOut(ETLJobBase):
    id: str
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # list/get/put/toggle 端点由 ORM 关系（lazy=selectin）自动嵌套；前端读 .name
    data_source: Optional[DataSourceOut] = None
    target_table: Optional[TargetTableOut] = None

    class Config:
        from_attributes = True


class ETLJobRunOut(BaseModel):
    id: str
    etl_job_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_rows: Optional[int] = None
    output_rows: Optional[int] = None
    error_rows: int = 0
    executed_sql: Optional[str] = None
    error_log: dict = {}
    stats: dict = {}
    trace_id: Optional[str] = None
    created_at: datetime
    # runs 端点由 ORM 关系自动嵌套；前端读 .job_name
    etl_job: Optional[ETLJobOut] = None

    class Config:
        from_attributes = True
