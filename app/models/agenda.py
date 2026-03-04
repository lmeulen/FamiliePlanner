"""Agenda / calendar event model."""
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AgendaEvent(Base):
    __tablename__ = "agenda_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    # Optional link to a family member; NULL = whole-family event
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True
    )
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
