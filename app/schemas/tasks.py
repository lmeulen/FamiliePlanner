"""Pydantic schemas for TaskList, TaskRecurrenceSeries and Task."""
from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator
from app.enums import RecurrenceType


# ---- TaskList ----

class TaskListBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = "#4ECDC4"
    sort_order: int = 0


class TaskListCreate(TaskListBase):
    pass


class TaskListUpdate(TaskListBase):
    pass


class TaskListReorderItem(BaseModel):
    id: int
    sort_order: int


class TaskListOut(TaskListBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OverduePositionOut(BaseModel):
    sort_order: int


# ---- TaskRecurrenceSeries ----

class TaskRecurrenceSeriesCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date

    @model_validator(mode="after")
    def end_after_start(self) -> "TaskRecurrenceSeriesCreate":
        if self.series_end <= self.series_start:
            raise ValueError("series_end must be after series_start")
        return self


class TaskRecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation."""
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_end: date


class TaskRecurrenceSeriesOut(BaseModel):
    id: int
    title: str
    description: str
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Task ----

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    done: bool = False
    due_date: date | None = None
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    pass


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    done: bool
    due_date: date | None = None
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    series_id: int | None = None
    is_exception: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}

