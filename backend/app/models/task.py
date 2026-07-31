"""执行任务 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class ExecutionTask(Base):
    __tablename__ = "execution_tasks"
    __table_args__ = (
        Index("ix_execution_tasks_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_name: Mapped[str | None] = mapped_column(String(200))
    source_id: Mapped[str | None] = mapped_column(String(100))
    template_id: Mapped[str | None] = mapped_column(String(100))
    query_params: Mapped[dict] = mapped_column(JSON, default=dict)
    executed_sql: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    output_format: Mapped[str] = mapped_column(String(20), default="xlsx")
    output_file: Mapped[str | None] = mapped_column(String(500))
    input_rows: Mapped[int | None] = mapped_column(Integer)
    output_rows: Mapped[int | None] = mapped_column(Integer)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error_log: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
