"""add_rd_expenses_table

Revision ID: 6282a4e3fe91
Revises: a1b2c3d4e5f6
Create Date: 2026-05-01 10:21:01.214700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6282a4e3fe91'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('rd_expenses',
        sa.Column('rd_no', sa.String(length=30), nullable=False, comment='研发费用编号'),
        sa.Column('project_id', sa.Integer(), nullable=True, comment='所属研发项目'),
        sa.Column('finance_record_id', sa.Integer(), nullable=True, comment='关联原始支出记录'),
        sa.Column('contract_id', sa.Integer(), nullable=True, comment='关联合同'),
        sa.Column('rd_category', sa.String(length=30), nullable=False, comment='费用大类（税法六大类）'),
        sa.Column('rd_sub_category', sa.String(length=50), nullable=True, comment='子分类（细粒度）'),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False, comment='费用金额（不含税）'),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=True, comment='税额'),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=True, comment='价税合计'),
        sa.Column('expense_date', sa.Date(), nullable=False, comment='费用发生日期'),
        sa.Column('accounting_period', sa.String(length=7), nullable=True, comment='会计期间 YYYY-MM'),
        sa.Column('description', sa.Text(), nullable=True, comment='费用说明'),
        sa.Column('vendor_name', sa.String(length=200), nullable=True, comment='供应商/收款方名称'),
        sa.Column('invoice_no', sa.String(length=50), nullable=True, comment='凭证号/发票号'),
        sa.Column('has_invoice', sa.Boolean(), nullable=True, comment='是否取得有效凭证'),
        sa.Column('invoice_type', sa.String(length=20), nullable=True, comment='凭证类型'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='审核状态'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注信息'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['finance_record_id'], ['finance_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rd_expenses_accounting_period'), 'rd_expenses', ['accounting_period'], unique=False)
    op.create_index(op.f('ix_rd_expenses_expense_date'), 'rd_expenses', ['expense_date'], unique=False)
    op.create_index(op.f('ix_rd_expenses_project_id'), 'rd_expenses', ['project_id'], unique=False)
    op.create_index(op.f('ix_rd_expenses_rd_category'), 'rd_expenses', ['rd_category'], unique=False)
    op.create_index(op.f('ix_rd_expenses_rd_no'), 'rd_expenses', ['rd_no'], unique=True)
    op.create_index(op.f('ix_rd_expenses_status'), 'rd_expenses', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('rd_expenses')
