"""执行任务 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class ExecutionTask(Base):
    __tablename__ = "execution_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_name: Mapped[str | None] = mapped_column(String(200))
    source_id: Mapped[str | None] = mapped_column(String(100))
    template_id: Mapped[str | None] = mapped_column(String(100))
    query_params: Mapped[dict] = mapped_column(JSON, default=dict)
    executed_sql: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
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
        DateTime, server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_name": self.task_name,
            "source_id": self.source_id,
            "template_id": self.template_id,
            "query_params": self.query_params,
            "status": self.status,
            "output_format": self.output_format,
            "output_file": self.output_file,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "error_rows": self.error_rows,
            "stats": self.stats,
            "duration_ms": self.duration_ms,
            "created_by": self.created_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
