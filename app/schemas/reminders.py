"""Pydantic schemas for standalone Reminders."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReminderBase(BaseModel):
    title: str = Field(..., max_length=500)
    notes: Optional[str] = None
    reminder_time: datetime
    is_completed: bool = False
    repeat: str = Field(default="none")  # none, daily, weekly, monthly
    is_archived: bool = Field(default=False)


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    reminder_time: Optional[datetime] = None
    is_completed: Optional[bool] = None
    repeat: Optional[str] = None
    is_archived: Optional[bool] = None


class ReminderResponse(ReminderBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
