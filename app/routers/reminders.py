"""
Reminders router — CRUD for standalone quick reminders.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, Reminder
from app.schemas.reminders import ReminderCreate, ReminderUpdate, ReminderResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/", response_model=List[ReminderResponse])
async def list_reminders(
    is_completed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reminders, optionally filtered by completion status."""
    query = select(Reminder).where(
        Reminder.user_id == current_user.id,
        Reminder.is_archived == False,
    )

    if is_completed is not None:
        query = query.where(Reminder.is_completed == is_completed)

    query = query.order_by(Reminder.reminder_time.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = Reminder(**payload.model_dump(), user_id=current_user.id)
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    return reminder


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_reminder(reminder_id, current_user.id, db)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = await _get_owned_reminder(reminder_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reminder, field, value)
    await db.flush()
    await db.refresh(reminder)
    return reminder


@router.post("/{reminder_id}/complete", response_model=ReminderResponse)
async def toggle_complete(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle the completion status of a reminder."""
    reminder = await _get_owned_reminder(reminder_id, current_user.id, db)
    reminder.is_completed = not reminder.is_completed
    await db.flush()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = await _get_owned_reminder(reminder_id, current_user.id, db)
    await db.delete(reminder)


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_owned_reminder(reminder_id: int, user_id: int, db: AsyncSession) -> Reminder:
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder
