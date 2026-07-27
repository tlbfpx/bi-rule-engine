"""数据源配置 ORM 模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.utils.crypto import encrypt, decrypt


class DataSource(Base):
    __tablename__ = "data_sources"

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

    # 抽取配置
    extract_mode: Mapped[str] = mapped_column(String(20), default="table")  # table | sql
    extract_sql: Mapped[str | None] = mapped_column(Text)
    extract_table: Mapped[str | None] = mapped_column(String(200))
    incremental_column: Mapped[str | None] = mapped_column(String(100))
    incremental_value: Mapped[str | None] = mapped_column(String(500))

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
            "extract_mode": self.extract_mode,
            "extract_sql": self.extract_sql,
            "extract_table": self.extract_table,
            "incremental_column": self.incremental_column,
            "incremental_value": self.incremental_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_password:
            data["db_password"] = self.db_password
        return data
