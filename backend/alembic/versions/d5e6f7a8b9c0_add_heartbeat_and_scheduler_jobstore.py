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
    # 1. etl_job_runs 增加 heartbeat_at 字段
    op.add_column('etl_job_runs', sa.Column('heartbeat_at', sa.DateTime, nullable=True))

    # 2. APScheduler SQLAlchemyJobStore 表
    # APScheduler 会自动创建这张表，但显式定义确保 alembic 迁移一致性
    op.create_table(
        'apscheduler_jobs',
        sa.Column('id', sa.String(191), primary_key=True),
        sa.Column('next_run_time', sa.DateTime, nullable=True),
        sa.Column('job_state', sa.LargeBinary, nullable=False),
    )
    op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'])


def downgrade() -> None:
    op.drop_index('ix_apscheduler_jobs_next_run_time', table_name='apscheduler_jobs')
    op.drop_table('apscheduler_jobs')
    op.drop_column('etl_job_runs', 'heartbeat_at')
