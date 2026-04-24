"""
Notes router — full CRUD + pin toggle + search.
All endpoints require authentication.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_db
from app.models.models import User, Note, Task, Priority
from app.schemas.notes import NoteCreate, NoteUpdate, NoteResponse
from app.schemas.tasks import TaskResponse
from app.schemas.workflow import NoteToTaskRequest
from app.core.security import get_current_user
from app.services.ownership import validate_project_assignment

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("/", response_model=List[NoteResponse])
async def list_notes(
    search: Optional[str] = Query(None, description="Search in title and content"),
    folder: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    pinned_first: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all notes for the current user. Supports search, folder, tag filters."""
    query = select(Note).where(Note.user_id == current_user.id, Note.is_archived == False)

    if search:
        query = query.where(
            or_(Note.title.ilike(f"%{search}%"), Note.content.ilike(f"%{search}%"))
        )
    if folder:
        query = query.where(Note.folder == folder)
    if project_id is not None:
        query = query.where(Note.project_id == project_id)

    if pinned_first:
        query = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc())
    else:
        query = query.order_by(Note.updated_at.desc())

    result = await db.execute(query)
    notes = result.scalars().all()

    # Filter by tag post-query (JSON field)
    if tag:
        notes = [n for n in notes if tag in (n.tags or [])]

    return notes


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_project_assignment(
        db,
        user_id=current_user.id,
        project_id=payload.project_id,
    )
    note = Note(**payload.model_dump(), user_id=current_user.id)
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await _get_owned_note(note_id, current_user.id, db)
    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await _get_owned_note(note_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    if "project_id" in update_data:
        await validate_project_assignment(
            db,
            user_id=current_user.id,
            project_id=update_data["project_id"],
        )
    for field, value in update_data.items():
        setattr(note, field, value)
    await db.flush()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await _get_owned_note(note_id, current_user.id, db)
    await db.delete(note)


@router.patch("/{note_id}/pin", response_model=NoteResponse)
async def toggle_pin(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle the pinned state of a note."""
    note = await _get_owned_note(note_id, current_user.id, db)
    note.is_pinned = not note.is_pinned
    await db.flush()
    await db.refresh(note)
    return note


@router.post("/{note_id}/archive", response_model=NoteResponse)
async def archive_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a note instead of deleting it."""
    note = await _get_owned_note(note_id, current_user.id, db)
    note.is_archived = True
    await db.flush()
    await db.refresh(note)
    return note


@router.post("/{note_id}/convert-to-task", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def convert_note_to_task(
    note_id: int,
    payload: NoteToTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await _get_owned_note(note_id, current_user.id, db)
    task_title = (payload.line_text or note.title or "Task from note").strip()
    task = Task(
        user_id=current_user.id,
        project_id=payload.project_id if payload.project_id is not None else note.project_id,
        title=task_title[:500],
        description=note.content,
        priority=Priority(payload.priority),
        source_note_id=note.id,
        source_note_line=payload.line_text,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_owned_note(note_id: int, user_id: int, db: AsyncSession) -> Note:
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
