"""ETL 任务执行记录 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ETLJobRun(Base):
    __tablename__ = "etl_job_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    etl_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("etl_jobs.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/completed/failed

    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    input_rows: Mapped[int | None] = mapped_column(Integer)
    output_rows: Mapped[int | None] = mapped_column(Integer)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)

    executed_sql: Mapped[str | None] = mapped_column(Text)
    error_log: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)

    # 链路追踪
    trace_id: Mapped[str | None] = mapped_column(String(32), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    etl_job: Mapped["ETLJob"] = relationship("ETLJob", lazy="selectin")
