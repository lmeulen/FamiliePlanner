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
    color: str = "#4ECDC4"
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    start_time_of_day: time
    end_time_of_day: time

    @model_validator(mode="after")
    def end_after_start(self) -> "RecurrenceSeriesCreate":
        if self.series_end <= self.series_start:
            raise ValueError("series_end must be after series_start")
        return self


class RecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation; all other fields may be updated."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    all_day: bool = False
    member_ids: list[int] = Field(default_factory=list)
    color: str = "#4ECDC4"
    recurrence_type: RecurrenceType
    series_end: date
    start_time_of_day: time
    end_time_of_day: time


class RecurrenceSeriesOut(BaseModel):
    id: int
    title: str
    description: str
    location: str
    all_day: bool
    member_ids: list[int] = Field(default_factory=list)
    color: str
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    start_time_of_day: time
    end_time_of_day: time
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
    color: str = "#4ECDC4"

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
    color: str
    series_id: int | None = None
    is_exception: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
