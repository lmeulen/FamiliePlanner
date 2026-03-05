"""Add photos table

Revision ID: b1c3d5e7f901
Revises: 52a321b44f51
Create Date: 2026-03-05
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b1c3d5e7f901'
down_revision: Union[str, Sequence[str], None] = '52a321b44f51'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename'),
    )


def downgrade() -> None:
    op.drop_table('photos')
