"""目标表 Pydantic Schema"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class TargetTableBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    db_host: str = Field(..., max_length=200)
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str = Field(..., max_length=200)
    db_username: str = Field(..., max_length=200)
    table_name: str = Field(..., max_length=200)
    write_mode: str = Field(default="append", pattern="^(append|truncate_insert|upsert)$")
    upsert_keys: List[str] = Field(default_factory=list)
    auto_create_table: bool = True


class TargetTableCreate(TargetTableBase):
    db_password: str = Field(..., min_length=1)


class TargetTableUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    db_host: Optional[str] = Field(default=None, max_length=200)
    db_port: Optional[int] = Field(default=None, ge=1, le=65535)
    db_name: Optional[str] = Field(default=None, max_length=200)
    db_username: Optional[str] = Field(default=None, max_length=200)
    db_password: Optional[str] = None
    table_name: Optional[str] = Field(default=None, max_length=200)
    write_mode: Optional[str] = Field(default=None, pattern="^(append|truncate_insert|upsert)$")
    upsert_keys: Optional[List[str]] = None
    auto_create_table: Optional[bool] = None


class TargetTableOut(TargetTableBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TargetTableTestRequest(BaseModel):
    db_host: str
    db_port: int = 3306
    db_name: str
    db_username: str
    db_password: str
    table_name: str
    write_mode: str = "append"
