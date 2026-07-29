"""映射表 Pydantic Schema"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class LookupTableCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    source_type: str = "upload"
    columns: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)


class LookupTableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[dict] = None
    data: Optional[dict] = None


class LookupTableOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    columns: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    row_count: int = 0
    created_at: datetime
    updated_at: datetime
