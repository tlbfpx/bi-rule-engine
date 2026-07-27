"""审计日志 ORM 模型（可选，默认关闭）"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class AuditLog(Base):
    """操作审计日志表 — 记录关键操作的审计轨迹"""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trace_id: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # CREATE / UPDATE / DELETE / EXECUTE
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # rule / datasource / etl_job / target_table
    resource_id: Mapped[str | None] = mapped_column(String(36))
    operator: Mapped[str | None] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
