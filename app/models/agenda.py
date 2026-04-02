"""Agenda / calendar event model – includes recurring series support."""

from datetime import datetime, time

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, Time, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import RecurrenceType

# ── Many-to-many junction tables ────────────────────────────────────────────

recurrence_series_members = Table(
    "recurrence_series_members",
    Base.metadata,
    Column("series_id", Integer, ForeignKey("recurrence_series.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("family_members.id", ondelete="CASCADE"), primary_key=True),
)

agenda_event_members = Table(
    "agenda_event_members",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("agenda_events.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("family_members.id", ondelete="CASCADE"), primary_key=True),
)


class RecurrenceSeries(Base):
    """Stores the recurrence rule for a series of agenda events."""

    __tablename__ = "recurrence_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_type: Mapped[RecurrenceType] = mapped_column(SAEnum(RecurrenceType), nullable=False)
    series_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    series_end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    start_time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    end_time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    interval: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_pattern: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rrule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    members = relationship("FamilyMember", secondary=recurrence_series_members, lazy="selectin", uselist=True)

    @property
    def member_ids(self) -> list[int]:
        return [m.id for m in (self.members or [])]


class AgendaEvent(Base):
    __tablename__ = "agenda_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    # Recurring series linkage (NULL = standalone event)
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recurrence_series.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    members = relationship("FamilyMember", secondary=agenda_event_members, lazy="selectin", uselist=True)

    @property
    def member_ids(self) -> list[int]:
        return [m.id for m in (self.members or [])]
