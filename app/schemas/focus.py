from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class FocusSessionCreate(BaseModel):
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    duration_seconds: int = Field(..., gt=0)

class FocusSessionResponse(FocusSessionCreate):
    id: int
    user_id: int
    is_archived: bool
    created_at: datetime

    model_config = {"from_attributes": True}
