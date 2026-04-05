"""create settings table

Revision ID: 475cd73e5207
Revises: 27631e007880
Create Date: 2026-04-05 19:12:22.876411

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "475cd73e5207"
down_revision: Union[str, Sequence[str], None] = "27631e007880"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("settings")
