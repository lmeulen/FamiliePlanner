"""Pydantic schemas for TaskList, TaskRecurrenceSeries and Task."""
from datetime import date, datetime
from pydantic import BaseModel
from app.enums import RecurrenceType


# ---- TaskList ----

class TaskListBase(BaseModel):
    name: str
    color: str = "#4ECDC4"


class TaskListCreate(TaskListBase):
    pass


class TaskListUpdate(TaskListBase):
    pass


class TaskListOut(TaskListBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- TaskRecurrenceSeries ----

class TaskRecurrenceSeriesCreate(BaseModel):
    title: str
    description: str = ""
    list_id: int | None = None
    member_id: int | None = None
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date


class TaskRecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation."""
    title: str
    description: str = ""
    list_id: int | None = None
    member_id: int | None = None
    recurrence_type: RecurrenceType
    series_end: date


class TaskRecurrenceSeriesOut(TaskRecurrenceSeriesCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Task ----

class TaskBase(BaseModel):
    title: str
    description: str = ""
    done: bool = False
    due_date: date | None = None
    list_id: int | None = None
    member_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    pass


class TaskOut(TaskBase):
    id: int
    created_at: datetime
    series_id: int | None = None
    is_exception: bool = False

    model_config = {"from_attributes": True}
