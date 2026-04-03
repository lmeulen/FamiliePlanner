"""Pydantic schemas for Birthday."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class BirthdayBase(BaseModel):
    """Base birthday schema."""

    name: str = Field(min_length=1, max_length=200)
    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int | None = Field(default=None, ge=1900, le=2100)
    year_type: str = Field(default="no_year")  # "no_year", "birth_year", "death_year"
    show_in_agenda: bool = True
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_date_and_year_type(self) -> "BirthdayBase":
        """Validate day is valid for month and year_type consistency."""
        # Validate day is valid for month
        if self.month in [4, 6, 9, 11] and self.day == 31:
            raise ValueError(f"Maand {self.month} heeft maximaal 30 dagen")
        if self.month == 2 and self.day > 29:
            raise ValueError("Februari heeft maximaal 29 dagen")

        # Validate year_type consistency
        if self.year_type in ["birth_year", "death_year"] and self.year is None:
            raise ValueError(f"Jaar is verplicht voor year_type '{self.year_type}'")
        if self.year_type not in ["no_year", "birth_year", "death_year"]:
            raise ValueError("year_type moet 'no_year', 'birth_year', of 'death_year' zijn")

        return self


class BirthdayCreate(BirthdayBase):
    """Schema for creating a birthday."""

    pass


class BirthdayUpdate(BirthdayBase):
    """Schema for updating a birthday."""

    pass


class BirthdayOut(BirthdayBase):
    """Schema for birthday output."""

    id: int
    created_at: datetime
    series_id: int | None
    # Computed properties (read-only)
    age: int | None = None
    years_since_death: int | None = None
    days_until_next: int = 0

    model_config = {"from_attributes": True}
