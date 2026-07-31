"""MySQL 数据源读取工具"""
import polars as pl
from sqlalchemy import create_engine, text
from loguru import logger
from app.config import get_settings

settings = get_settings()


def read_mysql_query(
    host: str, port: int, database: str,
    username: str, password: str,
    query: str,
    params: dict | None = None,
) -> pl.DataFrame:
    """从 MySQL 读取查询结果到 Polars DataFrame

    Args:
        params: 可选的参数化查询绑定参数（推荐使用，避免 SQL 注入）
    """
    connection_uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    logger.info(f"MySQL 查询: {host}:{port}/{database}")
    logger.debug(f"SQL: {query[:200]}...")

    engine = create_engine(connection_uri, pool_pre_ping=True, pool_recycle=3600)
    try:
        with engine.connect() as conn:
            if params:
                df = pl.read_database(
                    query=text(query), connection=conn,
                    execute_options={"parameters": params},
                )
            else:
                df = pl.read_database(query=text(query), connection=conn)
    finally:
        engine.dispose()

    if len(df) > settings.MAX_QUERY_ROWS:
        logger.warning(f"查询结果 {len(df)} 行超过上限 {settings.MAX_QUERY_ROWS}，已截断")
        df = df.head(settings.MAX_QUERY_ROWS)

    logger.info(f"MySQL 读取完成: {len(df)} 行, {len(df.columns)} 列")
    return df
