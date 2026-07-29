"""规则配置 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_set_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_label: Mapped[str | None] = mapped_column(String(200))
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    lookup_table_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    depends_on: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_set_id": self.rule_set_id,
            "field_name": self.field_name,
            "field_label": self.field_label,
            "rule_type": self.rule_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "config": self.config if isinstance(self.config, dict) else {},
            "lookup_table_id": self.lookup_table_id,
            "depends_on": self.depends_on or [],
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
