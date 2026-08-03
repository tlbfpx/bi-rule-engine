"""add heartbeat_at to etl_job_runs and apscheduler_jobs table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-03 11:00:00.000000

变更内容:
1. etl_job_runs 表新增 heartbeat_at 字段（ETL 执行期间定期更新，配合 Reaper 检测卡死任务）
2. 新建 apscheduler_jobs 表（APScheduler SQLAlchemyJobStore 持久化调度状态，重启恢复）
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import inspect
    from sqlalchemy import inspect as sa_inspect

    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # 1. etl_job_runs 增加 heartbeat_at 字段（幂等）
    columns = [c['name'] for c in inspector.get_columns('etl_job_runs')]
    if 'heartbeat_at' not in columns:
        op.add_column('etl_job_runs', sa.Column('heartbeat_at', sa.DateTime, nullable=True))

    # 2. APScheduler SQLAlchemyJobStore 表（幂等 — APScheduler 可能已自动创建）
    tables = inspector.get_table_names()
    if 'apscheduler_jobs' not in tables:
        op.create_table(
            'apscheduler_jobs',
            sa.Column('id', sa.String(191), primary_key=True),
            sa.Column('next_run_time', sa.DateTime, nullable=True),
            sa.Column('job_state', sa.LargeBinary, nullable=False),
        )

    indexes = [i['name'] for i in inspector.get_indexes('apscheduler_jobs')] if 'apscheduler_jobs' in tables else []
    if 'ix_apscheduler_jobs_next_run_time' not in indexes:
        try:
            op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'])
        except Exception:
            pass  # 索引可能已存在


def downgrade() -> None:
    try:
        op.drop_index('ix_apscheduler_jobs_next_run_time', table_name='apscheduler_jobs')
    except Exception:
        pass
    op.drop_table('apscheduler_jobs')
    op.drop_column('etl_job_runs', 'heartbeat_at')
