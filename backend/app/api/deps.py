"""API 依赖注入"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
