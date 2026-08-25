"""add google calendar sync tables

Revision ID: f5b2d8c4e7a9
Revises: a1c3e5g7i9k1
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5b2d8c4e7a9"
down_revision: Union[str, Sequence[str], None] = "a1c3e5g7i9k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_sync_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_key", sa.String(length=120), nullable=False),
        sa.Column("google_event_id", sa.String(length=1024), nullable=False),
        sa.Column("google_calendar_id", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("recurring_event_id", sa.String(length=1024), nullable=True),
        sa.Column("original_start", sa.String(length=40), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_key", name="uq_google_sync_links_entity"),
    )
    op.create_index("ix_google_sync_links_id", "google_sync_links", ["id"])
    op.create_index("ix_google_sync_links_entity_key", "google_sync_links", ["entity_key"])

    op.create_table(
        "google_sync_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_key", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_key", name="uq_google_sync_queue_entity"),
    )
    op.create_index("ix_google_sync_queue_id", "google_sync_queue", ["id"])
    op.create_index("ix_google_sync_queue_entity_key", "google_sync_queue", ["entity_key"])
    op.create_index("ix_google_sync_queue_next_attempt_at", "google_sync_queue", ["next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_google_sync_queue_next_attempt_at", table_name="google_sync_queue")
    op.drop_index("ix_google_sync_queue_entity_key", table_name="google_sync_queue")
    op.drop_index("ix_google_sync_queue_id", table_name="google_sync_queue")
    op.drop_table("google_sync_queue")

    op.drop_index("ix_google_sync_links_entity_key", table_name="google_sync_links")
    op.drop_index("ix_google_sync_links_id", table_name="google_sync_links")
    op.drop_table("google_sync_links")
