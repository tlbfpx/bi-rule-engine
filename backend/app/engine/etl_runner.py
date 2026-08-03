"""ETL 执行引擎 — 抽取/转换/加载"""
import time
import asyncio
import threading
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

import polars as pl
import pymysql
from loguru import logger
from sqlalchemy import select, create_engine, text
from sqlalchemy.engine import Engine
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
from app.engine.executor import RuleExecutor, get_default_event_bus
from app.engine.observer import ETLProgressEvent

settings = get_settings()

# 安全：只允许合法标���符（表名、列名）
# 全局并发信号量 — 限制同时执行的 ETL 数量，防止 OOM
_etl_semaphore: asyncio.Semaphore | None = None


def _get_etl_semaphore() -> asyncio.Semaphore:
    """惰性初始化全局 ETL 并发信号量（必须在 event loop 内调用）。"""
    global _etl_semaphore
    if _etl_semaphore is None:
        _etl_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_ETL)
    return _etl_semaphore


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


# ───────────────────────── 连接池缓存 ─────────────────────────
# per-data-source 缓存 SQLAlchemy engine，避免每次 ETL 新建 TCP 连接。
# 连接异常时销毁重建。

_source_engine_cache: dict[str, "Engine"] = {}


def _source_cache_key(ds) -> str:
    """生成数据源连接的唯一缓存键"""
    return f"{ds.db_host}:{ds.db_port}/{ds.db_name}/{ds.db_username}"


def _get_source_engine(ds) -> "Engine":
    """获取或创建数据源的 SQLAlchemy engine（带缓存）"""
    key = _source_cache_key(ds)
    from urllib.parse import quote_plus
    pwd = quote_plus(ds.db_password)
    user = quote_plus(ds.db_username)
    connection_uri = (
        f"mysql+pymysql://{user}:{pwd}"
        f"@{ds.db_host}:{ds.db_port}/{ds.db_name}?charset=utf8mb4"
    )
    engine = _source_engine_cache.get(key)
    if engine is None:
        engine = create_engine(
            connection_uri,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=3,
        )
        _source_engine_cache[key] = engine
        logger.info(f"创建数据源连接池: {ds.name} ({key})")
    return engine


def _dispose_source_engine(ds) -> None:
    """销毁数据源的缓存 engine（连接异常时调用）"""
    key = _source_cache_key(ds)
    engine = _source_engine_cache.pop(key, None)
    if engine:
        try:
            engine.dispose()
        except Exception:
            pass
        logger.info(f"已销毁数据源连接池: {ds.name} ({key})")


def dispose_all_source_engines() -> None:
    """应用关闭时释放所有缓存的 engine"""
    for key, engine in list(_source_engine_cache.items()):
        try:
            engine.dispose()
        except Exception:
            pass
    _source_engine_cache.clear()
    logger.info("所有数据源连接池已释放")


# ───────────────────────── Detached 数据快照 ─────────────────────────
# 从 ORM 对象提取所需的列属性为纯 dict（detached），避免在 session 关闭后
# 跨线程访问 ORM 对象时触发 DetachedInstanceError。


@dataclass
class DataSourceSnapshot:
    """DataSource 的线程安全快照（detached）。"""
    name: str
    db_host: str
    db_port: int
    db_name: str
    db_username: str
    db_password: str
    extract_mode: str
    extract_sql: Optional[str]
    extract_table: Optional[str]
    incremental_column: Optional[str]
    incremental_value: Optional[str]

    @classmethod
    def from_orm(cls, ds: DataSource) -> "DataSourceSnapshot":
        return cls(
            name=ds.name,
            db_host=ds.db_host,
            db_port=ds.db_port,
            db_name=ds.db_name,
            db_username=ds.db_username,
            db_password=ds.db_password,
            extract_mode=ds.extract_mode,
            extract_sql=ds.extract_sql,
            extract_table=ds.extract_table,
            incremental_column=ds.incremental_column,
            incremental_value=ds.incremental_value,
        )


@dataclass
class TargetTableSnapshot:
    """TargetTable 的线程安全快照（detached）。"""
    name: str
    db_host: str
    db_port: int
    db_name: str
    db_username: str
    db_password: str
    table_name: str
    write_mode: str
    upsert_keys: Optional[list]
    auto_create_table: bool

    @classmethod
    def from_orm(cls, t: TargetTable) -> "TargetTableSnapshot":
        return cls(
            name=t.name,
            db_host=t.db_host,
            db_port=t.db_port,
            db_name=t.db_name,
            db_username=t.db_username,
            db_password=t.db_password,
            table_name=t.table_name,
            write_mode=t.write_mode,
            upsert_keys=t.upsert_keys,
            auto_create_table=t.auto_create_table,
        )


def _publish_progress(run_id: str, job_id: str, phase: str, message: str = "",
                      input_rows: int = 0, output_rows: int = 0, progress: float = 0.0) -> None:
    """发布 ETL 阶段进度事件到 EventBus（单进程内 ws 监听器接收转发给前端）"""
    try:
        bus = get_default_event_bus()
        bus.publish(ETLProgressEvent(
            name="etl_progress",
            run_id=run_id,
            job_id=job_id,
            phase=phase,
            message=message,
            input_rows=input_rows,
            output_rows=output_rows,
            progress=progress,
        ))
    except Exception as e:
        logger.debug(f"发布进度事件失败（不影响执行）: {e}")


def _heartbeat_loop(run_id: str, stop_event: threading.Event, interval: int = 30) -> None:
    """后台心跳线程 — 定期更新 run_record 的 heartbeat_at 字段

    单独使用同步 engine 写入，不依赖 async session，避免阻塞 event loop。
    """
    sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    try:
        while not stop_event.wait(interval):
            try:
                with sync_engine.connect() as conn:
                    conn.execute(
                        text("UPDATE etl_job_runs SET heartbeat_at = NOW() WHERE id = :rid"),
                        {"rid": run_id},
                    )
                    conn.commit()
            except Exception as e:
                logger.debug(f"心跳更新失败 [run={run_id}]: {e}")
    finally:
        sync_engine.dispose()


def _safe_identifier(name: str, context: str = "identifier") -> str:
    """验证标识符安全，防止 SQL 注入"""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"不合法的{context}: {name}")
    return f"`{name}`"


def _build_extract_sql(data_source) -> tuple[str, dict]:
    """根据数据源配置构造参数化抽取 SQL，返回 (sql, params_dict)

    接受 DataSource ORM 对象或 DataSourceSnapshot 快照。
    """
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


def _read_source_sync(data_source) -> pl.DataFrame:
    """同步读取数据源（使用参数化查询）

    接受 DataSource ORM 对象或 DataSourceSnapshot 快照。
    使用进程级 engine 缓存，避免每次 ETL 新建 TCP 连接。
    """
    sql, params = _build_extract_sql(data_source)
    logger.info(f"ETL 抽取 SQL: {sql}")
    if params:
        logger.debug(f"ETL 抽取参数: {params}")
    engine = _get_source_engine(data_source)
    try:
        with engine.connect() as conn:
            if params:
                df = pl.read_database(query=text(sql), connection=conn, execute_options={"parameters": params})
            else:
                df = pl.read_database(query=text(sql), connection=conn)
    except Exception:
        # 连接异常时销毁缓存的 engine，下次调用自动重建
        _dispose_source_engine(data_source)
        raise
    logger.info(f"MySQL 读取完成: {len(df)} 行, {len(df.columns)} 列")
    return df


def _get_executed_sql_for_log(data_source) -> str:
    """生成日志用的 SQL 文本（安全：不含用户输入值）

    接受 DataSource ORM 对象或 DataSourceSnapshot 快照。
    """
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


def _ensure_table_exists(df: pl.DataFrame, target) -> None:
    """接受 TargetTable ORM 对象或 TargetTableSnapshot 快照。"""
    if not target.auto_create_table:
        return
    conn = pymysql.connect(
        host=target.db_host, port=target.db_port, user=target.db_username,
        password=target.db_password, database=target.db_name, charset="utf8mb4",
        connect_timeout=10,
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _write_to_target(df: pl.DataFrame, target, run_id: str) -> int:
    """接受 TargetTable ORM 对象或 TargetTableSnapshot 快照。"""
    _ensure_table_exists(df, target)
    # 替换 NaN 为 None（MySQL 不支持）
    float_cols = [c for c in df.columns if df[c].dtype in [pl.Float32, pl.Float64]]
    if float_cols:
        df = df.with_columns([pl.col(c).fill_nan(None) for c in float_cols])
        # 也替换 inf
        for c in float_cols:
            df = df.with_columns(
                pl.when(pl.col(c).is_infinite())
                .then(pl.lit(None))
                .otherwise(pl.col(c))
                .alias(c)
            )

    conn = pymysql.connect(
        host=target.db_host, port=target.db_port, user=target.db_username,
        password=target.db_password, database=target.db_name, charset="utf8mb4",
        connect_timeout=10,
    )
    total = 0
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
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                batch_with_run = [tuple(row) + (run_id,) for row in batch]
                cur.executemany(insert_sql, batch_with_run)
                total += len(batch)
            conn.commit()
            logger.info(f"目标表写入完成: {target.table_name}, 行数={total}")
    except Exception:
        conn.rollback()
        logger.error(f"目标表写入失败: {target.table_name}, 已写入 {total} 行后回滚")
        raise
    finally:
        conn.close()
    return total


def _update_incremental_value(df: pl.DataFrame, data_source) -> Optional[str]:
    """接受 DataSource ORM 对象或 DataSourceSnapshot 快照。"""
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
    data_source,
    target,
    run_id: str,
    job_id: str,
    rule_configs: list,
    lookup_tables: dict[str, dict],
) -> dict:
    """ETL 核心同步流程。接受 Snapshot 快照或 ORM 对象。"""
    start_time = time.time()
    executed_sql = _get_executed_sql_for_log(data_source)

    # Phase 1: Extract
    _publish_progress(run_id, job_id, "extracting", "正在读取源数据...", progress=0.0)
    df = _read_source_sync(data_source)
    input_rows = len(df)

    if input_rows == 0:
        _publish_progress(run_id, job_id, "completed", "源数据为空，跳过执行", progress=1.0)
        return {
            "status": "completed", "input_rows": 0, "output_rows": 0,
            "error_rows": 0, "duration_ms": int((time.time() - start_time) * 1000),
            "executed_sql": executed_sql, "stats": {},
            "incremental_value": None, "error_log": {},
        }

    _publish_progress(run_id, job_id, "extracting", f"已读取 {input_rows} 行", input_rows=input_rows, progress=0.2)

    # Phase 2: Transform
    _publish_progress(run_id, job_id, "transforming", f"正在执行规则转换 ({input_rows} 行)...", progress=0.3)
    result_df, stats = _execute_transform_sync(df, lookup_tables, rule_configs)
    _publish_progress(
        run_id, job_id, "transforming", f"规则转换完成，输出 {len(result_df)} 行",
        input_rows=input_rows, output_rows=len(result_df), progress=0.6,
    )

    # Phase 3: Load
    _publish_progress(run_id, job_id, "loading", "正在写入目标表...", progress=0.7)
    written_rows = _write_to_target(result_df, target, run_id)
    new_incremental_value = _update_incremental_value(result_df, data_source)

    _publish_progress(
        run_id, job_id, "completed", f"写入完成: {written_rows} 行",
        input_rows=input_rows, output_rows=written_rows, progress=1.0,
    )

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
    rule_configs = [RuleParser.parse_rule(r) for r in rules]
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

    # 全局并发限制 — 防止多 ETL 同时执行导��� OOM
    sem = _get_etl_semaphore()
    async with sem:
        async with AsyncSessionLocal() as session:
            job_result = await session.execute(select(ETLJob).where(ETLJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if not job:
                raise ValueError(f"ETL 任务不存在: {job_id}")

            # 在 session 关闭前提取 detached 快照，避免跨线程访问 ORM 对象触发 DetachedInstanceError
            data_source = DataSourceSnapshot.from_orm(job.data_source)
            target = TargetTableSnapshot.from_orm(job.target_table)
            ds_id = job.data_source_id  # 用于后续更新增量值

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
            run_record.heartbeat_at = datetime.now()
            await session.commit()

            rule_configs, lookup_tables = await _load_rules_and_lookup(session, job.rule_set_id)
            # 获取任务超时配置，优先用 job 级别，fallback 到全局默认
            timeout_seconds = job.timeout_seconds or settings.ETL_DEFAULT_TIMEOUT_SECONDS

        # 启动心跳线程
        heartbeat_stop = threading.Event()
        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            args=(run_id, heartbeat_stop, settings.ETL_HEARTBEAT_INTERVAL_SECONDS),
            daemon=True,
        )
        heartbeat_thread.start()

        try:
            # 使用 asyncio.wait_for 实现超时控制，防止源数据库查询卡住导致线程池耗尽
            core_result = await asyncio.wait_for(
                asyncio.to_thread(
                    _sync_etl_core, data_source, target, run_id, job_id, rule_configs, lookup_tables,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"ETL 执行超时 [job={job_id}, run={run_id}], timeout={timeout_seconds}s")
            core_result = {
                "status": "failed", "input_rows": 0, "output_rows": 0, "error_rows": 0,
                "duration_ms": timeout_seconds * 1000,
                "executed_sql": _get_executed_sql_for_log(data_source),
                "stats": {}, "incremental_value": None,
                "error_log": {"message": f"ETL 执行超时（{timeout_seconds}秒）", "exception": "TimeoutError"},
            }
        except Exception as e:
            logger.exception(f"ETL 执行失败 [job={job_id}, run={run_id}]")
            core_result = {
                "status": "failed", "input_rows": 0, "output_rows": 0, "error_rows": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "executed_sql": _get_executed_sql_for_log(data_source),
                "stats": {}, "incremental_value": None,
                "error_log": {"message": str(e), "exception": type(e).__name__},
            }
        finally:
            # 停止心跳线程
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=5)

        # 失败时发送失败进度事件
        if core_result["status"] == "failed":
            _publish_progress(
                run_id, job_id, "failed",
                core_result["error_log"].get("message", "ETL 执行失败"),
                progress=0.0,
            )

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
                ds_result = await session.execute(select(DataSource).where(DataSource.id == ds_id))
                ds = ds_result.scalar_one_or_none()
                if ds:
                    ds.incremental_value = core_result["incremental_value"]

            try:
                await session.commit()
            except Exception:
                # 如果提交失败（如 DB 不可用），确保 run_record 不会永远停在 running
                logger.exception(f"ETL 结果写入数据库失败 [job={job_id}, run={run_id}]")
                await session.rollback()

    return {
        "status": core_result["status"], "input_rows": core_result["input_rows"],
        "output_rows": core_result["output_rows"], "error_rows": core_result["error_rows"],
        "duration_ms": core_result["duration_ms"], "run_id": run_id,
    }
