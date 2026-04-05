"""add file_group_id to file_indexes

Revision ID: c934fe6814f0
Revises: 7dab35076a9c
Create Date: 2026-04-05 19:04:55.089239

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c934fe6814f0"
down_revision: Union[str, Sequence[str], None] = "7dab35076a9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Add column as nullable first to allow backfill
    with op.batch_alter_table("file_indexes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("file_group_id", sa.String(length=36), nullable=True))

    # Backfill: group existing records by (file_name, file_type), assign UUID per group
    result = conn.execute(sa.text("SELECT DISTINCT file_name, file_type FROM file_indexes WHERE is_deleted = 0"))
    groups = result.fetchall()

    for file_name, file_type in groups:
        group_id = str(uuid.uuid4())
        conn.execute(
            sa.text("UPDATE file_indexes SET file_group_id = :gid WHERE file_name = :fname AND file_type = :ftype"),
            {"gid": group_id, "fname": file_name, "ftype": file_type},
        )

    # Handle any remaining records (deleted ones) with individual UUIDs
    conn.execute(
        sa.text("UPDATE file_indexes SET file_group_id = :gid WHERE file_group_id IS NULL"), {"gid": str(uuid.uuid4())}
    )

    # Now make it NOT NULL
    with op.batch_alter_table("file_indexes", schema=None) as batch_op:
        batch_op.alter_column("file_group_id", nullable=False)
        batch_op.create_index(batch_op.f("ix_file_indexes_file_group_id"), ["file_group_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("file_indexes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_file_indexes_file_group_id"))
        batch_op.drop_column("file_group_id")
