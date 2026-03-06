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
    series_end: date | None = None
    interval: int = Field(default=1, ge=1, le=365)
    count: int | None = Field(default=None, ge=1, le=365)
    monthly_pattern: str | None = None
    rrule: str | None = None

    @model_validator(mode="after")
    def validate_recurrence(self) -> "TaskRecurrenceSeriesCreate":
        # Validate end condition: either count or series_end required
        if not self.count and not self.series_end:
            raise ValueError("Either count or series_end required")
        if self.count and self.series_end:
            raise ValueError("Cannot specify both count and series_end")

        # Validate series_end is after series_start when provided
        if self.series_end and self.series_end <= self.series_start:
            raise ValueError("series_end must be after series_start")

        return self


class TaskRecurrenceSeriesUpdate(BaseModel):
    """series_start is immutable after creation."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_end: date | None = None
    interval: int = Field(default=1, ge=1, le=365)
    count: int | None = Field(default=None, ge=1, le=365)
    monthly_pattern: str | None = None
    rrule: str | None = None

    @model_validator(mode="after")
    def validate_end_condition(self) -> "TaskRecurrenceSeriesUpdate":
        # Validate end condition: either count or series_end required
        if not self.count and not self.series_end:
            raise ValueError("Either count or series_end required")
        if self.count and self.series_end:
            raise ValueError("Cannot specify both count and series_end")
        return self


class TaskRecurrenceSeriesOut(BaseModel):
    id: int
    title: str
    description: str
    list_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)
    recurrence_type: RecurrenceType
    series_start: date
    series_end: date
    interval: int = 1
    count: int | None = None
    monthly_pattern: str | None = None
    rrule: str | None = None
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
