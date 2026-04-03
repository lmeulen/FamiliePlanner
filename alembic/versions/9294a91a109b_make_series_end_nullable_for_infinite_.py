"""make series_end nullable for infinite recurrences

Revision ID: 9294a91a109b
Revises: efa6f2fb3658
Create Date: 2026-04-02 22:19:04.367518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9294a91a109b'
down_revision: Union[str, Sequence[str], None] = 'efa6f2fb3658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make series_end nullable to support infinite recurrences."""
    # Use batch_alter_table for SQLite compatibility (CLAUDE.md #11)
    with op.batch_alter_table('recurrence_series') as batch_op:
        batch_op.alter_column('series_end',
                              existing_type=sa.Date(),
                              nullable=True)

    with op.batch_alter_table('task_recurrence_series') as batch_op:
        batch_op.alter_column('series_end',
                              existing_type=sa.Date(),
                              nullable=True)


def downgrade() -> None:
    """Revert series_end to NOT NULL."""
    # Assign far-future date to NULL values before making NOT NULL
    op.execute("UPDATE recurrence_series SET series_end = date('now', '+365 days') WHERE series_end IS NULL")
    op.execute("UPDATE task_recurrence_series SET series_end = date('now', '+365 days') WHERE series_end IS NULL")

    with op.batch_alter_table('recurrence_series') as batch_op:
        batch_op.alter_column('series_end',
                              existing_type=sa.Date(),
                              nullable=False)

    with op.batch_alter_table('task_recurrence_series') as batch_op:
        batch_op.alter_column('series_end',
                              existing_type=sa.Date(),
                              nullable=False)
