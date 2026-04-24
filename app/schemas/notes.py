"""Pydantic schemas for Notes."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    title: str = Field(default="Untitled Note", max_length=500)
    content: Optional[str] = None
    color: str = Field(default="#ffffff")
    folder: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    project_id: Optional[int] = None
    is_archived: bool = Field(default=False)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    folder: Optional[str] = None
    tags: Optional[List[str]] = None
    project_id: Optional[int] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class NoteResponse(NoteBase):
    id: int
    user_id: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
