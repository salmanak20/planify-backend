"""Pydantic schemas for Projects / Workspaces."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#435f92")
    parent_project_id: Optional[int] = None
    is_archived: bool = Field(default=False)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parent_project_id: Optional[int] = None
    is_archived: Optional[bool] = None


class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
