"""ETL 调度任务 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ETLJob(Base):
    __tablename__ = "etl_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    data_source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    target_table_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("target_tables.id", ondelete="RESTRICT"), nullable=False
    )
    rule_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_sets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 调度配置
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")
    error_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600)

    # 运行状态
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_run_status: Mapped[str | None] = mapped_column(String(20))
    last_run_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    data_source: Mapped["DataSource"] = relationship("DataSource", lazy="selectin")
    target_table: Mapped["TargetTable"] = relationship("TargetTable", lazy="selectin")
