"""目标表配置 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.utils.crypto import encrypt, decrypt


class TargetTable(Base):
    __tablename__ = "target_tables"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # 连接信息
    db_host: Mapped[str] = mapped_column(String(200), nullable=False)
    db_port: Mapped[int] = mapped_column(Integer, default=3306)
    db_name: Mapped[str] = mapped_column(String(200), nullable=False)
    db_username: Mapped[str] = mapped_column(String(200), nullable=False)
    _db_password: Mapped[str] = mapped_column("db_password", String(500), nullable=False)

    # 写入配置
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    write_mode: Mapped[str] = mapped_column(String(30), default="append")  # append | truncate_insert | upsert
    upsert_keys: Mapped[list] = mapped_column(JSON, default=list)
    auto_create_table: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def db_password(self) -> str:
        return decrypt(self._db_password)

    @db_password.setter
    def db_password(self, value: str):
        self._db_password = encrypt(value)

    def to_dict(self, include_password: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_username": self.db_username,
            "table_name": self.table_name,
            "write_mode": self.write_mode,
            "upsert_keys": self.upsert_keys,
            "auto_create_table": self.auto_create_table,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_password:
            data["db_password"] = self.db_password
        return data
