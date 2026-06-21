"""add cozi_uid to agenda_events, recurrence_series and meals

Revision ID: a1c3e5g7i9k1
Revises: 9294a91a109b
Create Date: 2026-06-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5g7i9k1"
down_revision: Union[str, Sequence[str], None] = "9294a91a109b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agenda_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cozi_uid", sa.String(500), nullable=True))
        batch_op.create_index("ix_agenda_events_cozi_uid", ["cozi_uid"], unique=False)

    with op.batch_alter_table("recurrence_series", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cozi_uid", sa.String(500), nullable=True))
        batch_op.create_index("ix_recurrence_series_cozi_uid", ["cozi_uid"], unique=False)

    with op.batch_alter_table("meals", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cozi_uid", sa.String(500), nullable=True))
        batch_op.create_index("ix_meals_cozi_uid", ["cozi_uid"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("meals", schema=None) as batch_op:
        batch_op.drop_index("ix_meals_cozi_uid")
        batch_op.drop_column("cozi_uid")

    with op.batch_alter_table("recurrence_series", schema=None) as batch_op:
        batch_op.drop_index("ix_recurrence_series_cozi_uid")
        batch_op.drop_column("cozi_uid")

    with op.batch_alter_table("agenda_events", schema=None) as batch_op:
        batch_op.drop_index("ix_agenda_events_cozi_uid")
        batch_op.drop_column("cozi_uid")
