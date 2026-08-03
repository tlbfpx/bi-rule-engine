"""add data_source_id to rule_sets

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-03 16:30:00.000000

变更内容:
1. rule_sets 表新增 data_source_id 字段（FK → data_sources.id，ON DELETE SET NULL）
2. 为 rule_sets.data_source_id 添加索引
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    columns = [c['name'] for c in inspector.get_columns('rule_sets')]
    if 'data_source_id' not in columns:
        op.add_column('rule_sets', sa.Column(
            'data_source_id', sa.String(36), nullable=True,
            sa.ForeignKey('data_sources.id', ondelete='SET NULL')
        ))
        op.create_index('idx_rule_sets_data_source_id', 'rule_sets', ['data_source_id'])


def downgrade() -> None:
    op.drop_index('idx_rule_sets_data_source_id', table_name='rule_sets')
    op.drop_constraint('fk_rule_sets_data_source', 'rule_sets', type_='foreignkey')
    op.drop_column('rule_sets', 'data_source_id')
