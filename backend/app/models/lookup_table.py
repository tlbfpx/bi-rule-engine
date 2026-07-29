"""映射表 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class LookupTable(Base):
    __tablename__ = "lookup_tables"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), default="upload")
    columns: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
