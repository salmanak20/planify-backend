from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import FocusSession, User
from app.core.security import get_current_user
from app.schemas.focus import FocusSessionCreate, FocusSessionResponse

router = APIRouter(prefix="/focus", tags=["focus"])

@router.post("/", response_model=FocusSessionResponse, status_code=status.HTTP_201_CREATED)
async def log_focus_session(
    payload: FocusSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = FocusSession(**payload.model_dump(), user_id=current_user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("/", response_model=List[FocusSessionResponse])
async def list_focus_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(FocusSession).where(FocusSession.user_id == current_user.id).order_by(FocusSession.start_time.desc())
    result = await db.execute(query)
    return result.scalars().all()
