from pydantic import BaseModel, Field


class NoteToTaskRequest(BaseModel):
    line_text: str | None = None
    project_id: int | None = None
    priority: str = "medium"


class SubtaskPatchItem(BaseModel):
    id: int | None = None
    title: str
    is_complete: bool = False


class SubtasksPatchRequest(BaseModel):
    subtasks: list[SubtaskPatchItem] = Field(default_factory=list)


class CreateTaskFromCalendarDayRequest(BaseModel):
    title: str
    day_iso: str
    project_id: int | None = None
    description: str | None = None

