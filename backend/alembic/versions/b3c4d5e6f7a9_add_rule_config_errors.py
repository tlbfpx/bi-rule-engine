"""add_rule_config_errors

Revision ID: b3c4d5e6f7a9
Revises: 91d3e8135c84
Create Date: 2026-08-04 13:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a9'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 rules 表新增 config_errors 列 — 预计算规则配置错误列表"""
    op.add_column(
        'rules',
        sa.Column(
            'config_errors',
            sa.JSON(),
            nullable=True,
            server_default=sa.text('(JSON_ARRAY())'),
            comment='规则配置完整性校验结果（创建/更��时预计算，列表端点直接读取）',
        ),
    )


def downgrade() -> None:
    op.drop_column('rules', 'config_errors')
