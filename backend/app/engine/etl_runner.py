"""ETL 执行引擎 — 抽取/转换/加载"""
import time
import asyncio
import re
from datetime import datetime
from typing import Optional

import polars as pl
import pymysql
from loguru import logger
from sqlalchemy import select, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.logging import get_trace_id, set_trace_id, generate_trace_id
from app.models.data_source import DataSource
from app.models.target_table import TargetTable
from app.models.etl_job import ETLJob
from app.models.etl_job_run import ETLJobRun
from app.models.rule import Rule
from app.models.lookup_table import LookupTable
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor

settings = get_settings()

# 安全：只允许合法标识符（表名、列名）
_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _safe_identifier(name: str, context: str = "identifier") -> str:
    """验证标识符安全，防止 SQL 注入"""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"不合法的{context}: {name}")
    return f"`{name}`"


def _build_extract_sql(data_source: DataSource) -> tuple[str, dict]:
    """根据数据源配置构造参数化抽取 SQL，返回 (sql, params_dict)"""
    params = {}

    if data_source.extract_mode == "sql" and data_source.extract_sql:
        sql = data_source.extract_sql.strip().rstrip(";")
        if data_source.incremental_column and data_source.incremental_value:
            col = _safe_identifier(data_source.incremental_column, "增量字段")
            where_clause = f"{col} > :inc_val"
            params["inc_val"] = data_source.incremental_value
            if " where " in sql.lower():
                sql = f"{sql} AND {where_clause}"
            else:
                sql = f"{sql} WHERE {where_clause}"
        return sql, params

    table = _safe_identifier(data_source.extract_table or data_source.name, "表名")
    sql = f"SELECT * FROM {table}"
    if data_source.incremental_column and data_source.incremental_value:
        col = _safe_identifier(data_source.incremental_column, "增量字段")
        sql += f" WHERE {col} > :inc_val"
        params["inc_val"] = data_source.incremental_value
    return sql, params


def _read_source_sync(data_source: DataSource) -> pl.DataFrame:
    """同步读取数据源（使用参数化查询）"""
    sql, params = _build_extract_sql(data_source)
    logger.info(f"ETL 抽取 SQL: {sql}, params={params}")
    connection_uri = (
        f"mysql+pymysql://{data_source.db_username}:{data_source.db_password}"
        f"@{data_source.db_host}:{data_source.db_port}/{data_source.db_name}"
        f"?charset=utf8mb4"
    )
    engine = create_engine(connection_uri, pool_pre_ping=True)
    with engine.connect() as conn:
        if params:
            df = pl.read_database(query=text(sql), connection=conn, execute_options={"parameters": params})
        else:
            df = pl.read_database(query=text(sql), connection=conn)
    logger.info(f"MySQL 读取完成: {len(df)} 行, {len(df.columns)} 列")
    return df


def _get_executed_sql_for_log(data_source: DataSource) -> str:
    """生成日志用的 SQL 文本（安全：不含用户输入值）"""
    if data_source.extract_mode == "sql" and data_source.extract_sql:
        return data_source.extract_sql.strip().rstrip(";")
    table = data_source.extract_table or data_source.name
    return f"SELECT * FROM `{table}`"


def _polars_to_mysql_type(pl_dtype) -> str:
    dtype_str = str(pl_dtype)
    if "Int" in dtype_str:
        return "BIGINT"
    if "Float" in dtype_str or "Double" in dtype_str:
        return "DOUBLE"
    if "Bool" in dtype_str:
        return "TINYINT(1)"
    if "Date" in dtype_str and "DateTime" not in dtype_str:
        return "DATE"
    if "DateTime" in dtype_str or "Time" in dtype_str:
        return "DATETIME(6)"
    return "VARCHAR(500)"


def _ensure_table_exists(df: pl.DataFrame, target: TargetTable) -> None:
    if not target.auto_create_table:
        return
    conn = pymysql.connect(
        host=target.db_host, port=target.db_port, user=target.db_username,
        password=target.db_password, database=target.db_name, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                (target.db_name, target.table_name),
            )
            if cur.fetchone():
                return
            columns = []
            for col in df.columns:
                mysql_type = _polars_to_mysql_type(df[col].dtype)
                columns.append(f"`{col}` {mysql_type}")
            columns.append("`_etl_run_id` VARCHAR(36) DEFAULT NULL")
            columns.append("`_etl_created_at` DATETIME DEFAULT CURRENT_TIMESTAMP")
            # 安全：表名已通过 _safe_identifier 在调用方验证
            create_sql = f"CREATE TABLE `{target.table_name}` ({', '.join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            logger.info(f"自动创建目标表: {target.db_name}.{target.table_name}")
            cur.execute(create_sql)
            conn.commit()
    finally:
        conn.close()


def _write_to_target(df: pl.DataFrame, target: TargetTable, run_id: str) -> int:
    _ensure_table_exists(df, target)
    # 替换 NaN 和 Inf 为 None（MySQL 不支持）
    df = df.with_columns([
        pl.col(c).fill_nan(None).fill_nan(None)
        for c in df.columns
        if df[c].dtype in [pl.Float32, pl.Float64]
    ])
    # 也替换 inf
    for c in df.columns:
        if df[c].dtype in [pl.Float32, pl.Float64]:
            df = df.with_columns(
                pl.when(pl.col(c).is_infinite())
                .then(pl.lit(None))
                .otherwise(pl.col(c))
                .alias(c)
            )

    conn = pymysql.connect(
        host=target.db_host, port=target.db_port, user=target.db_username,
        password=target.db_password, database=target.db_name, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            if target.write_mode == "truncate_insert":
                cur.execute(f"TRUNCATE TABLE `{target.table_name}`")

            columns = df.columns + ["_etl_run_id"]
            placeholders = ", ".join(["%s"] * len(columns))
            col_names = ", ".join([f"`{c}`" for c in columns])

            if target.write_mode == "upsert" and target.upsert_keys:
                update_cols = [c for c in df.columns if c not in target.upsert_keys]
                if update_cols:
                    update_clause = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols])
                    insert_sql = (
                        f"INSERT INTO `{target.table_name}` ({col_names}) VALUES ({placeholders}) "
                        f"ON DUPLICATE KEY UPDATE {update_clause}"
                    )
                else:
                    insert_sql = f"INSERT IGNORE INTO `{target.table_name}` ({col_names}) VALUES ({placeholders})"
            else:
                insert_sql = f"INSERT INTO `{target.table_name}` ({col_names}) VALUES ({placeholders})"

            rows = df.to_numpy().tolist()
            batch_size = settings.ETL_BATCH_SIZE
            total = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                batch_with_run = [tuple(row) + (run_id,) for row in batch]
                cur.executemany(insert_sql, batch_with_run)
                total += len(batch)
            conn.commit()
            logger.info(f"目标表写入完成: {target.table_name}, 行数={total}")
            return total
    finally:
        conn.close()


def _update_incremental_value(df: pl.DataFrame, data_source: DataSource) -> Optional[str]:
    col = data_source.incremental_column
    if not col or col not in df.columns or len(df) == 0:
        return None
    try:
        max_val = df[col].max()
        if max_val is None:
            return None
        return str(max_val)
    except Exception as e:
        logger.warning(f"计算增量值失败: {e}")
        return None


def _execute_transform_sync(
    df: pl.DataFrame,
    lookup_tables: dict[str, dict],
    rule_configs: list,
) -> tuple[pl.DataFrame, dict]:
    executor = RuleExecutor(rule_configs, lookup_tables)
    result_df, stats = executor.execute(df)
    return result_df, stats.to_dict()


def _sync_etl_core(
    data_source: DataSource,
    target: TargetTable,
    run_id: str,
    rule_configs: list,
    lookup_tables: dict[str, dict],
) -> dict:
    start_time = time.time()
    executed_sql = _get_executed_sql_for_log(data_source)

    df = _read_source_sync(data_source)
    input_rows = len(df)

    if input_rows == 0:
        return {
            "status": "completed", "input_rows": 0, "output_rows": 0,
            "error_rows": 0, "duration_ms": int((time.time() - start_time) * 1000),
            "executed_sql": executed_sql, "stats": {},
            "incremental_value": None, "error_log": {},
        }

    result_df, stats = _execute_transform_sync(df, lookup_tables, rule_configs)
    output_rows = len(result_df)
    written_rows = _write_to_target(result_df, target, run_id)
    new_incremental_value = _update_incremental_value(result_df, data_source)

    return {
        "status": "completed", "input_rows": input_rows,
        "output_rows": written_rows, "error_rows": 0,
        "duration_ms": int((time.time() - start_time) * 1000),
        "executed_sql": executed_sql, "stats": stats,
        "incremental_value": new_incremental_value, "error_log": {},
    }


async def _load_rules_and_lookup(session: AsyncSession, rule_set_id: str | None = None):
    """加载规则和映射表。如果指定 rule_set_id，只加载该规则集下的规则。"""
    rule_query = select(Rule).where(Rule.enabled == True)
    if rule_set_id:
        rule_query = rule_query.where(Rule.rule_set_id == rule_set_id)
    rule_query = rule_query.order_by(Rule.priority.asc())
    rule_result = await session.execute(rule_query)
    rules = rule_result.scalars().all()
    lt_result = await session.execute(select(LookupTable))
    lookup_tables = {str(t.id): t.data for t in lt_result.scalars().all()}
    rule_configs = [RuleParser.parse(r.to_dict()) for r in rules]
    return rule_configs, lookup_tables


async def run_etl_job(job_id: str, run_id: Optional[str] = None,
                      trace_id: Optional[str] = None) -> dict:
    """执行 ETL 任务的入口函数

    Args:
        job_id: ETL 任务 ID
        run_id: 可选，已有的执行记录 ID
        trace_id: 可选，请求链路追踪 ID（调度触发时自动生成，API 触发时从 HTTP 请求继承）
    """
    start_time = time.time()

    # 设置 trace_id：优先使用传入的，其次当前上下文，最后生成新的
    if trace_id:
        set_trace_id(trace_id)
    else:
        current = get_trace_id()
        if not current:
            set_trace_id(generate_trace_id())

    logger.info(f"开始执行 ETL 任务: job={job_id}, run={run_id}")

    async with AsyncSessionLocal() as session:
        job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise ValueError(f"ETL 任务不存在: {job_id}")

        data_source = job.data_source
        target = job.target_table

        if run_id is None:
            run_record = ETLJobRun(
                etl_job_id=job_id,
                status="pending",
                trace_id=get_trace_id(),
            )
            session.add(run_record)
            await session.flush()
            await session.refresh(run_record)
            run_id = str(run_record.id)
        else:
            run_result = await session.execute(select(ETLJobRun).where(ETLJobRun.id == run_id))
            run_record = run_result.scalar_one_or_none()
            if not run_record:
                raise ValueError(f"执行记录不存在: {run_id}")

        run_record.status = "running"
        run_record.started_at = datetime.now()
        await session.commit()

        rule_configs, lookup_tables = await _load_rules_and_lookup(session, job.rule_set_id)

    try:
        core_result = await asyncio.to_thread(
            _sync_etl_core, data_source, target, run_id, rule_configs, lookup_tables,
        )
    except Exception as e:
        logger.exception(f"ETL 执行失败 [job={job_id}, run={run_id}]")
        core_result = {
            "status": "failed", "input_rows": 0, "output_rows": 0, "error_rows": 0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "executed_sql": _get_executed_sql_for_log(data_source),
            "stats": {}, "incremental_value": None,
            "error_log": {"message": str(e), "exception": type(e).__name__},
        }

    async with AsyncSessionLocal() as session:
        run_result = await session.execute(select(ETLJobRun).where(ETLJobRun.id == run_id))
        run_record = run_result.scalar_one_or_none()
        if run_record:
            run_record.status = core_result["status"]
            run_record.completed_at = datetime.now()
            run_record.duration_ms = core_result["duration_ms"]
            run_record.input_rows = core_result["input_rows"]
            run_record.output_rows = core_result["output_rows"]
            run_record.error_rows = core_result["error_rows"]
            run_record.executed_sql = core_result["executed_sql"]
            run_record.stats = core_result["stats"]
            run_record.error_log = core_result["error_log"]

        job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
        job = job_result.scalar_one_or_none()
        if job:
            job.last_run_at = datetime.now()
            job.last_run_status = core_result["status"]
            job.last_run_error = core_result["error_log"].get("message")

        if core_result["incremental_value"]:
            ds_result = await session.execute(select(DataSource).where(DataSource.id == data_source.id))
            ds = ds_result.scalar_one_or_none()
            if ds:
                ds.incremental_value = core_result["incremental_value"]

        await session.commit()

    return {
        "status": core_result["status"], "input_rows": core_result["input_rows"],
        "output_rows": core_result["output_rows"], "error_rows": core_result["error_rows"],
        "duration_ms": core_result["duration_ms"], "run_id": run_id,
    }
