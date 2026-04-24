"""Pydantic schemas for Tasks."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from app.models.models import Priority


class SubtaskResponse(BaseModel):
    id: int
    title: str
    is_complete: bool
    model_config = {"from_attributes": True}


class TaskBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    project_id: Optional[int] = None
    event_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    source_note_id: Optional[int] = None
    source_note_line: Optional[str] = None
    is_archived: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_deadline_and_reminder(self):
        if (
            self.deadline is not None
            and self.reminder_at is not None
            and self.reminder_at > self.deadline
        ):
            raise ValueError("reminder_at must be before or equal to deadline")
        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    is_complete: Optional[bool] = None
    tags: Optional[List[str]] = None
    deadline: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    project_id: Optional[int] = None
    event_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    is_archived: Optional[bool] = None

    @model_validator(mode="after")
    def validate_partial_deadline_and_reminder(self):
        if (
            self.deadline is not None
            and self.reminder_at is not None
            and self.reminder_at > self.deadline
        ):
            raise ValueError("reminder_at must be before or equal to deadline")
        return self


class TaskResponse(TaskBase):
    id: int
    user_id: int
    is_complete: bool
    subtasks: List[SubtaskResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
