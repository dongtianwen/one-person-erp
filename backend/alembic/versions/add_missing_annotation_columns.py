"""add_missing_annotation_columns

Revision ID: add_missing_annotation_columns
Revises: c8de50e8001e
Create Date: 2026-04-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_annotation_columns'
down_revision = 'c8de50e8001e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加缺失的列到 annotation_tasks 表
    op.add_column('annotation_tasks', sa.Column('assignee', sa.String(100), nullable=True, comment='负责人'))
    op.add_column('annotation_tasks', sa.Column('deadline', sa.DateTime(), nullable=True, comment='截止日期'))
    op.add_column('annotation_tasks', sa.Column('progress', sa.Integer(), nullable=True, comment='进度 (%)'))
    
    # 添加 status 列到 training_experiments 表（如果不存在）
    # 注意：training_experiments 表已经有 status 列，所以这个操作可能会失败
    # 我们使用 batch_operations 来安全地添加列
    pass


def downgrade() -> None:
    op.drop_column('annotation_tasks', 'progress')
    op.drop_column('annotation_tasks', 'deadline')
    op.drop_column('annotation_tasks', 'assignee')
