"""Google Calendar one-way sync bookkeeping (FamiliePlanner -> Google)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GoogleSyncLink(Base):
    """Maps a FamiliePlanner entity to the Google Calendar event mirroring it."""

    __tablename__ = "google_sync_links"
    __table_args__ = (UniqueConstraint("entity_type", "entity_key", name="uq_google_sync_links_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # "event" | "series" | "instance_override"
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Stable natural key, e.g. "event:412" or "series:7:2026-08-25" - never a churning row id.
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    google_event_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    google_calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    recurring_event_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    original_start: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class GoogleSyncQueue(Base):
    """Outbox of pending pushes; one row per entity, collapsing rapid edits."""

    __tablename__ = "google_sync_queue"
    __table_args__ = (UniqueConstraint("entity_type", "entity_key", name="uq_google_sync_queue_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(10), nullable=False)  # "upsert" | "delete"
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
