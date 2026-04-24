from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    id: int
    type: str
    title: str
    subtitle: str | None = None
    project_id: int | None = None


class GlobalSearchResponse(BaseModel):
    tasks: list[SearchItem] = Field(default_factory=list)
    notes: list[SearchItem] = Field(default_factory=list)
    events: list[SearchItem] = Field(default_factory=list)
    projects: list[SearchItem] = Field(default_factory=list)

