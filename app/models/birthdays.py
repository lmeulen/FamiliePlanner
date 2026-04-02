"""Birthday model."""

from datetime import date, datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Birthday(Base):
    """Birthday model for managing birthdays and memorials."""

    __tablename__ = "birthdays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-31
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1-12
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Optional year
    year_type: Mapped[str] = mapped_column(String(20), default="no_year")  # "no_year", "birth_year", "death_year"
    show_in_agenda: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    # Link to agenda series (nullable, cascade delete)
    series_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("recurrence_series.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    @property
    def age(self) -> int | None:
        """Calculate current age for birth_year type."""
        if not self.year or self.year_type != "birth_year":
            return None
        today = date.today()
        age = today.year - self.year
        # Adjust if birthday hasn't occurred yet this year
        if (today.month, today.day) < (self.month, self.day):
            age -= 1
        return age

    @property
    def years_since_death(self) -> int | None:
        """Calculate years since death for death_year type."""
        if not self.year or self.year_type != "death_year":
            return None
        return date.today().year - self.year

    @property
    def days_until_next(self) -> int:
        """Calculate days until next birthday occurrence."""
        today = date.today()
        try:
            this_year_birthday = date(today.year, self.month, self.day)
        except ValueError:
            # Feb 29 in non-leap year: use Mar 1
            this_year_birthday = date(today.year, 3, 1)

        if this_year_birthday >= today:
            return (this_year_birthday - today).days
        else:
            try:
                next_year_birthday = date(today.year + 1, self.month, self.day)
            except ValueError:
                # Feb 29 in non-leap year
                next_year_birthday = date(today.year + 1, 3, 1)
            return (next_year_birthday - today).days

    @property
    def next_birthday_date(self) -> date:
        """Get the next occurrence date."""
        today = date.today()
        try:
            this_year = date(today.year, self.month, self.day)
            return this_year if this_year >= today else date(today.year + 1, self.month, self.day)
        except ValueError:
            # Feb 29 in non-leap year
            return date(today.year if date(today.year, 3, 1) >= today else today.year + 1, 3, 1)
