from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """数据库会话依赖注入。

    事务管理策略：endpoint 内部自行 commit/flush，此处仅在仍有活跃事务时
    做 fallback commit（覆盖未显式提交的只读查询场景）。异常时自动回滚。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # fallback：仅在 session 仍有活跃事务时提交（不与 endpoint 内显式 commit 冲突）
            if session.in_transaction():
                await session.commit()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
