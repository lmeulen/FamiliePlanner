"""remove agenda event and recurrence color columns

Revision ID: d4f9c1a2b7e3
Revises: c2d4e6f8a012
Create Date: 2026-03-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f9c1a2b7e3"
down_revision: Union[str, Sequence[str], None] = "c2d4e6f8a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agenda_events", schema=None) as batch_op:
        batch_op.drop_column("color")

    with op.batch_alter_table("recurrence_series", schema=None) as batch_op:
        batch_op.drop_column("color")


def downgrade() -> None:
    with op.batch_alter_table("recurrence_series", schema=None) as batch_op:
        batch_op.add_column(sa.Column("color", sa.String(length=7), nullable=False, server_default="#4ECDC4"))

    with op.batch_alter_table("agenda_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("color", sa.String(length=7), nullable=False, server_default="#4ECDC4"))
