"""Pydantic schemas for AgendaEvent."""
from datetime import datetime
from pydantic import BaseModel, model_validator


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

    model_config = {"from_attributes": True}
