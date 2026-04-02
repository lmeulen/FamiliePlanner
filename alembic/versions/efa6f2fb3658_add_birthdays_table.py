"""Add birthdays table.

Revision ID: efa6f2fb3658
Revises: e3a5b7c9d1f2
Create Date: 2026-04-02 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "efa6f2fb3658"
down_revision: Union[str, None] = "e3a5b7c9d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create birthdays table."""
    op.create_table(
        "birthdays",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("year_type", sa.String(20), server_default="no_year"),
        sa.Column("show_in_agenda", sa.Boolean(), server_default="1"),
        sa.Column("notes", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("recurrence_series.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    """Drop birthdays table."""
    op.drop_table("birthdays")
