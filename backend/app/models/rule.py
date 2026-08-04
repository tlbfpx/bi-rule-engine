"""规则配置 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        # 复合索引：按规则集查询启用的规则（高频查询模式）
        Index("ix_rules_set_enabled_priority", "rule_set_id", "enabled", "priority"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_sets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_label: Mapped[str | None] = mapped_column(String(200))
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    lookup_table_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("lookup_tables.id", ondelete="SET NULL"), nullable=True, index=True
    )
    depends_on: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    config_errors: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list,
        comment="规则配置完整性校验结果（创建/更新时预计算，列表端点直接读取）"
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
