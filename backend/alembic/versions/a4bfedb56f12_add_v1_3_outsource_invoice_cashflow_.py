"""add_v1_3_outsource_invoice_cashflow_fields

Revision ID: a4bfedb56f12
Revises: 43b5f12ec9ec
Create Date: 2026-04-06 07:38:45.905977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4bfedb56f12'
down_revision: Union[str, Sequence[str], None] = '43b5f12ec9ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # contracts 表新增字段
    with op.batch_alter_table('contracts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expected_payment_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('payment_stage_note', sa.String(length=200), nullable=True))

    # finance_records 表新增字段
    with op.batch_alter_table('finance_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('outsource_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('has_invoice', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('tax_treatment', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('invoice_direction', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('invoice_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('tax_rate', sa.Numeric(precision=5, scale=4), nullable=True))
        batch_op.add_column(sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=True))

    # v1.3 索引
    with op.batch_alter_table('contracts', schema=None) as batch_op:
        batch_op.create_index('idx_contracts_expected_payment_date', ['expected_payment_date'])

    with op.batch_alter_table('finance_records', schema=None) as batch_op:
        batch_op.create_index('idx_finance_records_invoice_direction', ['invoice_direction'])
        batch_op.create_index('idx_finance_records_invoice_no', ['invoice_no'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('finance_records', schema=None) as batch_op:
        batch_op.drop_index('idx_finance_records_invoice_no')
        batch_op.drop_index('idx_finance_records_invoice_direction')

    with op.batch_alter_table('contracts', schema=None) as batch_op:
        batch_op.drop_index('idx_contracts_expected_payment_date')

    with op.batch_alter_table('finance_records', schema=None) as batch_op:
        batch_op.drop_column('tax_amount')
        batch_op.drop_column('tax_rate')
        batch_op.drop_column('invoice_type')
        batch_op.drop_column('invoice_direction')
        batch_op.drop_column('tax_treatment')
        batch_op.drop_column('has_invoice')
        batch_op.drop_column('outsource_name')

    with op.batch_alter_table('contracts', schema=None) as batch_op:
        batch_op.drop_column('payment_stage_note')
        batch_op.drop_column('expected_payment_date')
