from datetime import datetime
from pydantic import BaseModel, Field


class DashboardTaskItem(BaseModel):
    id: int
    title: str
    deadline: datetime | None = None
    priority: str
    is_complete: bool


class DashboardEventItem(BaseModel):
    id: int
    title: str
    start_time: datetime
    end_time: datetime
    all_day: bool


class DashboardNoteItem(BaseModel):
    id: int
    title: str
    updated_at: datetime
    is_pinned: bool


class ActiveFocusSession(BaseModel):
    task_id: int | None = None
    task_title: str | None = None
    started_at: datetime | None = None
    remaining_seconds: int | None = None


class DashboardSummaryResponse(BaseModel):
    today_tasks: list[DashboardTaskItem] = Field(default_factory=list)
    upcoming_events: list[DashboardEventItem] = Field(default_factory=list)
    active_focus_session: ActiveFocusSession | None = None
    recent_notes: list[DashboardNoteItem] = Field(default_factory=list)


class ProjectActivityItem(BaseModel):
    item_type: str
    item_id: int
    title: str
    timestamp: datetime


class ProjectAnalyticsResponse(BaseModel):
    project_id: int
    progress_percent: float
    completed_tasks: int
    overdue_items: int
    recent_activity: list[ProjectActivityItem] = Field(default_factory=list)

