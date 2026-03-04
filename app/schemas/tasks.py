"""Pydantic schemas for TaskList and Task."""
from datetime import date, datetime
from pydantic import BaseModel


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

    model_config = {"from_attributes": True}
