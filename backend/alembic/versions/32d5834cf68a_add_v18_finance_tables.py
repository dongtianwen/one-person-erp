"""add_v18_finance_tables

Revision ID: 32d5834cf68a
Revises: a4bfedb56f12
Create Date: 2026-04-09 12:14:42.186978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32d5834cf68a'
down_revision: Union[str, Sequence[str], None] = 'a4bfedb56f12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """v1.8: export_batches 表添加 updated_at 和 is_deleted 列。"""
    with op.batch_alter_table('export_batches', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(),
            server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False,
        ))
        batch_op.add_column(sa.Column(
            'is_deleted', sa.Boolean(),
            server_default=sa.text('0'), nullable=False,
        ))


def downgrade() -> None:
    """回滚：移除 updated_at 和 is_deleted 列。"""
    with op.batch_alter_table('export_batches', schema=None) as batch_op:
        batch_op.drop_column('is_deleted')
        batch_op.drop_column('updated_at')
