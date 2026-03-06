"""Add extended recurrence patterns

Revision ID: c2d4e6f8a012
Revises: b1c3d5e7f901
Create Date: 2026-03-06
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c2d4e6f8a012'
down_revision: Union[str, Sequence[str], None] = 'b1c3d5e7f901'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to recurrence_series table
    op.add_column('recurrence_series', sa.Column('interval', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('recurrence_series', sa.Column('count', sa.Integer(), nullable=True))
    op.add_column('recurrence_series', sa.Column('monthly_pattern', sa.String(50), nullable=True))
    op.add_column('recurrence_series', sa.Column('rrule', sa.String(500), nullable=True))

    # Add new columns to task_recurrence_series table
    op.add_column('task_recurrence_series', sa.Column('interval', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('task_recurrence_series', sa.Column('count', sa.Integer(), nullable=True))
    op.add_column('task_recurrence_series', sa.Column('monthly_pattern', sa.String(50), nullable=True))
    op.add_column('task_recurrence_series', sa.Column('rrule', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove columns from task_recurrence_series table
    op.drop_column('task_recurrence_series', 'rrule')
    op.drop_column('task_recurrence_series', 'monthly_pattern')
    op.drop_column('task_recurrence_series', 'count')
    op.drop_column('task_recurrence_series', 'interval')

    # Remove columns from recurrence_series table
    op.drop_column('recurrence_series', 'rrule')
    op.drop_column('recurrence_series', 'monthly_pattern')
    op.drop_column('recurrence_series', 'count')
    op.drop_column('recurrence_series', 'interval')
