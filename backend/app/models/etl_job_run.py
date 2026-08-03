"""ETL 任务执行记录 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ETLJobRun(Base):
    __tablename__ = "etl_job_runs"
    __table_args__ = (
        Index("ix_etl_job_runs_job_created", "etl_job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    etl_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("etl_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending/running/completed/failed

    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)  # ETL 执行期间定期更新
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    input_rows: Mapped[int | None] = mapped_column(Integer)
    output_rows: Mapped[int | None] = mapped_column(Integer)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)

    executed_sql: Mapped[str | None] = mapped_column(Text)
    error_log: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)

    # 链路追踪
    trace_id: Mapped[str | None] = mapped_column(String(32), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    etl_job: Mapped["ETLJob"] = relationship("ETLJob", lazy="selectin")
