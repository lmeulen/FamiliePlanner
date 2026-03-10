"""Pydantic schemas for AgendaEvent and RecurrenceSeries."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field, model_validator

from app.enums import RecurrenceType

# ── Recurrence series ────────────────────────────────────────────


class RecurrenceSeriesCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    all_day: bool = False
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date | None = None
    start_time_of_day: time
    end_time_of_day: time
    interval: int = Field(default=1, ge=1, le=365)
    count: int | None = Field(default=None, ge=1, le=365)
    monthly_pattern: str | None = None
    rrule: str | None = None

    @model_validator(mode="after")
    def validate_recurrence(self) -> "RecurrenceSeriesCreate":
        # Validate end condition: either count or series_end required
        if not self.count and not self.series_end:
            raise ValueError("Either count or series_end required")
        if self.count and self.series_end:
            raise ValueError("Cannot specify both count and series_end")

        # Validate series_end is after series_start when provided
        if self.series_end and self.series_end <= self.series_start:
            raise ValueError("series_end must be after series_start")

        return self


class RecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation; all other fields may be updated."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    all_day: bool = False
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_end: date | None = None
    start_time_of_day: time
    end_time_of_day: time
    interval: int = Field(default=1, ge=1, le=365)
    count: int | None = Field(default=None, ge=1, le=365)
    monthly_pattern: str | None = None
    rrule: str | None = None

    @model_validator(mode="after")
    def validate_end_condition(self) -> "RecurrenceSeriesUpdate":
        # Validate end condition: either count or series_end required
        if not self.count and not self.series_end:
            raise ValueError("Either count or series_end required")
        if self.count and self.series_end:
            raise ValueError("Cannot specify both count and series_end")
        return self


class RecurrenceSeriesOut(BaseModel):
    id: int
    title: str
    description: str
    location: str
    all_day: bool
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    start_time_of_day: time
    end_time_of_day: time
    interval: int = 1
    count: int | None = None
    monthly_pattern: str | None = None
    rrule: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agenda event ─────────────────────────────────────────────────


class AgendaEventBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    member_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def end_after_start(self) -> "AgendaEventBase":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AgendaEventCreate(AgendaEventBase):
    pass


class AgendaEventUpdate(AgendaEventBase):
    pass


class AgendaEventOut(BaseModel):
    id: int
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    all_day: bool
    member_ids: list[int] = Field(default_factory=list)
    series_id: int | None = None
    is_exception: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
