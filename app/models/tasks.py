"""Task list model."""

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import RecurrenceType

# ── Many-to-many junction tables ────────────────────────────────────────────

task_recurrence_series_members = Table(
    "task_recurrence_series_members",
    Base.metadata,
    Column("series_id", Integer, ForeignKey("task_recurrence_series.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("family_members.id", ondelete="CASCADE"), primary_key=True),
)

task_members = Table(
    "task_members",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("family_members.id", ondelete="CASCADE"), primary_key=True),
)


class TaskList(Base):
    __tablename__ = "task_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class TaskRecurrenceSeries(Base):
    """Stores the recurrence rule for a series of tasks."""

    __tablename__ = "task_recurrence_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    list_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recurrence_type: Mapped[RecurrenceType] = mapped_column(SAEnum(RecurrenceType), nullable=False)
    series_start: Mapped[date] = mapped_column(Date, nullable=False)
    series_end: Mapped[date] = mapped_column(Date, nullable=False)
    interval: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_pattern: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rrule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    members = relationship("FamilyMember", secondary=task_recurrence_series_members, lazy="selectin", uselist=True)

    @property
    def member_ids(self) -> list[int]:
        return [m.id for m in (self.members or [])]


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # Optional link to list
    list_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Recurring series linkage (NULL = standalone task)
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_recurrence_series.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    members = relationship("FamilyMember", secondary=task_members, lazy="selectin", uselist=True)

    @property
    def member_ids(self) -> list[int]:
        return [m.id for m in (self.members or [])]
