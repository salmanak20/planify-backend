"""Pydantic schemas for Calendar Events."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class EventBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    color: str = Field(default="#435f92")
    project_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    reminder_at: Optional[datetime] = None
    all_day: bool = False
    repeat: str = "none"
    repeat_interval: int = 1
    repeat_weekdays: list[int] = Field(default_factory=list)
    recurrence_end: Optional[datetime] = None
    skipped_occurrences: list[str] = Field(default_factory=list)
    is_archived: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_times(self):
        if not self.all_day and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.reminder_at and self.reminder_at > self.start_time:
            raise ValueError("reminder_at must be before or equal to start_time")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    color: Optional[str] = None
    project_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    repeat: Optional[str] = None
    repeat_interval: Optional[int] = None
    repeat_weekdays: Optional[list[int]] = None
    recurrence_end: Optional[datetime] = None
    skipped_occurrences: Optional[list[str]] = None
    is_archived: Optional[bool] = None

    @model_validator(mode="after")
    def validate_partial_times(self):
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.all_day is not True
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time")
        if (
            self.reminder_at is not None
            and self.start_time is not None
            and self.reminder_at > self.start_time
        ):
            raise ValueError("reminder_at must be before or equal to start_time")
        return self


class EventResponse(EventBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
