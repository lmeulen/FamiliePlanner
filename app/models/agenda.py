"""Agenda / calendar event model – includes recurring series support."""
from datetime import datetime, time
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, Text, Date, Time, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.enums import RecurrenceType


class RecurrenceSeries(Base):
    """Stores the recurrence rule for a series of agenda events."""
    __tablename__ = "recurrence_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True
    )
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")
    recurrence_type: Mapped[RecurrenceType] = mapped_column(SAEnum(RecurrenceType), nullable=False)
    series_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    series_end: Mapped[datetime] = mapped_column(Date, nullable=False)
    start_time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    end_time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class AgendaEvent(Base):
    __tablename__ = "agenda_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True
    )
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")
    # Recurring series linkage (NULL = standalone event)
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recurrence_series.id", ondelete="CASCADE"), nullable=True
    )
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
