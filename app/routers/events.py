"""
Events router — full CRUD with date range filtering.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.models import User, Event
from app.schemas.events import EventCreate, EventUpdate, EventResponse
from app.core.security import get_current_user
from app.services.ownership import validate_project_assignment

router = APIRouter(prefix="/events", tags=["Calendar Events"])


@router.get("/", response_model=List[EventResponse])
async def list_events(
    start: Optional[datetime] = Query(None, description="Filter events from this datetime"),
    end: Optional[datetime] = Query(None, description="Filter events until this datetime"),
    project_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List events — optionally filtered to a date range (for calendar views)."""
    query = select(Event).where(Event.user_id == current_user.id, Event.is_archived == False)

    if start and end:
        # Events that overlap with the [start, end] window
        query = query.where(
            and_(Event.start_time < end, Event.end_time > start)
        )
    elif start:
        query = query.where(Event.end_time >= start)
    elif end:
        query = query.where(Event.start_time <= end)

    if project_id is not None:
        query = query.where(Event.project_id == project_id)

    query = query.order_by(Event.start_time.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_project_assignment(
        db,
        user_id=current_user.id,
        project_id=payload.project_id,
    )
    event = Event(**payload.model_dump(), user_id=current_user.id)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_event(event_id, current_user.id, db)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await _get_owned_event(event_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    effective_start = update_data.get("start_time", event.start_time)
    effective_end = update_data.get("end_time", event.end_time)
    effective_all_day = update_data.get("all_day", event.all_day)
    effective_reminder = update_data.get("reminder_at", event.reminder_at)
    if not effective_all_day and effective_end <= effective_start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    if effective_reminder is not None and effective_reminder > effective_start:
        raise HTTPException(status_code=400, detail="reminder_at must be before or equal to start_time")
    if "project_id" in update_data:
        await validate_project_assignment(
            db,
            user_id=current_user.id,
            project_id=update_data["project_id"],
        )
    for field, value in update_data.items():
        setattr(event, field, value)
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await _get_owned_event(event_id, current_user.id, db)
    await db.delete(event)


@router.post("/{event_id}/archive", response_model=EventResponse)
async def archive_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive an event instead of deleting it."""
    event = await _get_owned_event(event_id, current_user.id, db)
    event.is_archived = True
    await db.flush()
    await db.refresh(event)
    return event


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_owned_event(event_id: int, user_id: int, db: AsyncSession) -> Event:
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.user_id == user_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
