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
        String(36), ForeignKey("data_sources.id"), nullable=False
    )
    target_table_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("target_tables.id"), nullable=False
    )
    rule_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

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

    def to_dict(self, include_relations: bool = False) -> dict:
        data = {
            "id": self.id,
            "job_name": self.job_name,
            "description": self.description,
            "enabled": self.enabled,
            "data_source_id": self.data_source_id,
            "target_table_id": self.target_table_id,
            "rule_set_id": self.rule_set_id,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "error_retry_count": self.error_retry_count,
            "timeout_seconds": self.timeout_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_error": self.last_run_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_relations:
            data["data_source"] = self.data_source.to_dict() if self.data_source else None
            data["target_table"] = self.target_table.to_dict() if self.target_table else None
        return data
