"""数据源 Pydantic Schema"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class DataSourceBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    db_host: str = Field(..., max_length=200)
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str = Field(..., max_length=200)
    db_username: str = Field(..., max_length=200)
    extract_mode: str = Field(default="table", pattern="^(table|sql)$")
    extract_sql: Optional[str] = None
    extract_table: Optional[str] = Field(default=None, max_length=200)
    incremental_column: Optional[str] = Field(default=None, max_length=100)
    incremental_value: Optional[str] = Field(default=None, max_length=500)

    @field_validator("extract_sql", "extract_table", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


class DataSourceCreate(DataSourceBase):
    db_password: str = Field(..., min_length=1)


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    db_host: Optional[str] = Field(default=None, max_length=200)
    db_port: Optional[int] = Field(default=None, ge=1, le=65535)
    db_name: Optional[str] = Field(default=None, max_length=200)
    db_username: Optional[str] = Field(default=None, max_length=200)
    db_password: Optional[str] = None
    extract_mode: Optional[str] = Field(default=None, pattern="^(table|sql)$")
    extract_sql: Optional[str] = None
    extract_table: Optional[str] = Field(default=None, max_length=200)
    incremental_column: Optional[str] = Field(default=None, max_length=100)
    incremental_value: Optional[str] = Field(default=None, max_length=500)


class DataSourceOut(DataSourceBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DataSourceTestRequest(BaseModel):
    db_host: str
    db_port: int = 3306
    db_name: str
    db_username: str
    db_password: str
