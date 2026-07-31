"""全局业务常量枚举 — 魔法值全部枚举化（阿里规约）。

所有枚举值映射到现有 ORM 模型和 engine.constants 中的字符串值，
确保与数据库存储值一致。
"""
from enum import StrEnum


class RuleType(StrEnum):
    """规则类型枚举，映射到 engine.constants.RuleType 的值。

    - MAPPING: 字段映射
    - CLEANING: 数据清洗
    - LOOKUP: 查找替换
    - COMPUTED: 公式计算
    """

    MAPPING = "mapping"
    CLEANING = "cleaning"
    LOOKUP = "lookup"
    COMPUTED = "computed"


class ETLJobStatus(StrEnum):
    """ETL 调度任务状态枚举，映射到 etl_job_runs.status 的值。

    - PENDING: 待执行
    - RUNNING: 执行中
    - COMPLETED: 执行完成
    - FAILED: 执行失败
    - CANCELLED: 已取消
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    """执行任务状态枚举，映射到 execution_tasks.status 的值。

    - PENDING: 待执行
    - RUNNING: 执行中
    - COMPLETED: 执行完成
    - FAILED: 执行失败
    - CANCELLED: 已取消
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WriteMode(StrEnum):
    """目标表写入模式枚举，映射到 target_tables.write_mode 的值。

    - APPEND: 追加写入
    - TRUNCATE_INSERT: 先清空再写入
    - UPSERT: 更新或插入
    """

    APPEND = "append"
    TRUNCATE_INSERT = "truncate_insert"
    UPSERT = "upsert"


class ExtractMode(StrEnum):
    """数据源抽取模式枚举，映射到 data_sources.extract_mode 的值。

    - TABLE: 按表名抽取
    - SQL: 按 SQL 语句抽取
    """

    TABLE = "table"
    SQL = "sql"
