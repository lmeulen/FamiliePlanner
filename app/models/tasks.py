"""Task list model."""
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Boolean, Integer, ForeignKey, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.enums import RecurrenceType


class TaskList(Base):
    __tablename__ = "task_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class TaskRecurrenceSeries(Base):
    """Stores the recurrence rule for a series of tasks."""
    __tablename__ = "task_recurrence_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    list_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True
    )
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True
    )
    recurrence_type: Mapped[RecurrenceType] = mapped_column(SAEnum(RecurrenceType), nullable=False)
    series_start: Mapped[date] = mapped_column(Date, nullable=False)
    series_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Optional link to list and family member
    list_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True
    )
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True
    )
    # Recurring series linkage (NULL = standalone task)
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_recurrence_series.id", ondelete="CASCADE"), nullable=True
    )
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
