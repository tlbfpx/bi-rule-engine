"""rule depends_on: Text -> JSON

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-29 09:35:00.000000

depends_on 原存为 JSON 字符串（Text 列 + 应用层 json.dumps/loads），
改为原生 JSON 列：消除序列化样板，可在 DB 层查询依赖。既有值均为合法 JSON，
MySQL ALTER 会自动把文本解析为 JSON。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'rules', 'depends_on',
        existing_type=sa.Text(),
        type_=sa.JSON(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'rules', 'depends_on',
        existing_type=sa.JSON(),
        type_=sa.Text(),
        existing_nullable=True,
    )
