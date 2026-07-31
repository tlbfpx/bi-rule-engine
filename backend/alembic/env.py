from logging.config import fileConfig
import os
from urllib.parse import quote_plus
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db import Base
from app.models import (
    Rule, RuleSet, LookupTable, ExecutionTask,
    DataSource, TargetTable, ETLJob, ETLJobRun, AuditLog, User,
)  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 动态构建数据库 URL（从环境变量），不在 alembic.ini 中硬编码密码
_db_user = os.getenv("DB_USER", "bi_rule")
_db_pass = quote_plus(os.getenv("DB_PASSWORD", ""))
_db_host = os.getenv("DB_HOST", "localhost")
_db_port = os.getenv("DB_PORT", "3306")
_db_name = os.getenv("DB_NAME", "bi_rule_engine")
config.set_main_option(
    "sqlalchemy.url",
    f"mysql+pymysql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}?charset=utf8mb4",
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
