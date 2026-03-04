"""Pydantic schemas for AgendaEvent and RecurrenceSeries."""
from datetime import date, datetime, time
from pydantic import BaseModel, model_validator
from app.enums import RecurrenceType


# ── Recurrence series ────────────────────────────────────────────

class RecurrenceSeriesCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    all_day: bool = False
    member_id: int | None = None
    color: str = "#4ECDC4"
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    start_time_of_day: time
    end_time_of_day: time


class RecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation; all other fields may be updated."""
    title: str
    description: str = ""
    location: str = ""
    all_day: bool = False
    member_id: int | None = None
    color: str = "#4ECDC4"
    recurrence_type: RecurrenceType
    series_end: date
    start_time_of_day: time
    end_time_of_day: time


class RecurrenceSeriesOut(RecurrenceSeriesCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agenda event ─────────────────────────────────────────────────

class AgendaEventBase(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    member_id: int | None = None
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


class AgendaEventOut(AgendaEventBase):
    id: int
    created_at: datetime
    series_id: int | None = None
    is_exception: bool = False

    model_config = {"from_attributes": True}
