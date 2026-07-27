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
) -> pl.DataFrame:
    """从 MySQL 读取查询结果到 Polars DataFrame"""
    connection_uri = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    logger.info(f"MySQL 查询: {host}:{port}/{database}")
    logger.debug(f"SQL: {query[:200]}...")

    engine = create_engine(connection_uri, pool_pre_ping=True)
    with engine.connect() as conn:
        df = pl.read_database(query=text(query), connection=conn)

    if len(df) > settings.MAX_QUERY_ROWS:
        logger.warning(f"查询结果 {len(df)} 行超过上限 {settings.MAX_QUERY_ROWS}，已截断")
        df = df.head(settings.MAX_QUERY_ROWS)

    logger.info(f"MySQL 读取完成: {len(df)} 行, {len(df.columns)} 列")
    return df
