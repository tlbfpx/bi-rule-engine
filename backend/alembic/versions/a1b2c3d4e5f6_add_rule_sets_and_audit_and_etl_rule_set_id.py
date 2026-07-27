"""add rule_sets, audit_logs, etl_jobs.rule_set_id

Revision ID: a1b2c3d4e5f6
Revises: 91d3e8135c84
Create Date: 2026-07-24 16:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '91d3e8135c84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rules', sa.Column('rule_set_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_rules_rule_set_id'), 'rules', ['rule_set_id'], unique=False)
    op.add_column('etl_job_runs', sa.Column('trace_id', sa.String(length=32), nullable=True))
    op.create_index(op.f('ix_etl_job_runs_trace_id'), 'etl_job_runs', ['trace_id'], unique=False)
    op.create_table(
        'rule_sets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.add_column('etl_jobs', sa.Column('rule_set_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_etl_jobs_rule_set_id'), 'etl_jobs', ['rule_set_id'], unique=False)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('trace_id', sa.String(length=32), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('operator', sa.String(length=100), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_trace_id'), 'audit_logs', ['trace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_etl_job_runs_trace_id'), table_name='etl_job_runs')
    op.drop_column('etl_job_runs', 'trace_id')
    op.drop_index(op.f('ix_rules_rule_set_id'), table_name='rules')
    op.drop_column('rules', 'rule_set_id')
    op.drop_index(op.f('ix_audit_logs_trace_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_etl_jobs_rule_set_id'), table_name='etl_jobs')
    op.drop_column('etl_jobs', 'rule_set_id')
    op.drop_table('rule_sets')
