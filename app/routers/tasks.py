"""
Tasks router — full CRUD + complete toggle + subtask nesting.
Supports filters: priority, project_id, is_complete, tag.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import User, Task, Priority
from app.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse
from app.schemas.workflow import SubtasksPatchRequest, CreateTaskFromCalendarDayRequest
from app.core.security import get_current_user
from app.services.ownership import validate_task_links

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    priority: Optional[Priority] = Query(None),
    project_id: Optional[int] = Query(None),
    is_complete: Optional[bool] = Query(None),
    tag: Optional[str] = Query(None),
    parent_only: bool = Query(True, description="Only return top-level tasks (no subtasks)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Task)
        .options(selectinload(Task.subtasks))
        .where(Task.user_id == current_user.id, Task.is_archived == False)
    )
    if parent_only:
        query = query.where(Task.parent_task_id.is_(None))
    if priority:
        query = query.where(Task.priority == priority)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    if is_complete is not None:
        query = query.where(Task.is_complete == is_complete)

    query = query.order_by(Task.is_complete.asc(), Task.deadline.asc().nullslast(), Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    if tag:
        tasks = [t for t in tasks if tag in (t.tags or [])]

    return tasks


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_task_links(
        db,
        user_id=current_user.id,
        project_id=payload.project_id,
        event_id=payload.event_id,
        parent_task_id=payload.parent_task_id,
    )
    task = Task(**payload.model_dump(), user_id=current_user.id)
    db.add(task)
    await db.flush()
    # Reload with subtasks
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == task.id)
    )
    return result.scalar_one()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_task(task_id, current_user.id, db)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_owned_task(task_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    effective_deadline = update_data.get("deadline", task.deadline)
    effective_reminder = update_data.get("reminder_at", task.reminder_at)
    if (
        effective_deadline is not None
        and effective_reminder is not None
        and effective_reminder > effective_deadline
    ):
        raise HTTPException(status_code=400, detail="reminder_at must be before or equal to deadline")
    await validate_task_links(
        db,
        user_id=current_user.id,
        project_id=update_data.get("project_id", task.project_id),
        event_id=update_data.get("event_id", task.event_id),
        parent_task_id=update_data.get("parent_task_id", task.parent_task_id),
        current_task_id=task.id,
    )
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.flush()
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == task.id)
    )
    return result.scalar_one()


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_owned_task(task_id, current_user.id, db)
    await db.delete(task)


@router.patch("/{task_id}/archive", response_model=TaskResponse)
async def archive_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a task instead of deleting it."""
    task = await _get_owned_task(task_id, current_user.id, db)
    task.is_archived = True
    await db.flush()
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == task.id)
    )
    return result.scalar_one()


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def toggle_complete(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle the complete state of a task."""
    task = await _get_owned_task(task_id, current_user.id, db)
    task.is_complete = not task.is_complete
    task.completed_at = datetime.utcnow() if task.is_complete else None
    await db.flush()
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == task.id)
    )
    return result.scalar_one()


@router.patch("/{task_id}/subtasks", response_model=TaskResponse)
async def patch_subtasks(
    task_id: int,
    payload: SubtasksPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent = await _get_owned_task(task_id, current_user.id, db)
    existing_map = {subtask.id: subtask for subtask in parent.subtasks}
    keep_ids: set[int] = set()
    for item in payload.subtasks:
        if item.id and item.id in existing_map:
            subtask = existing_map[item.id]
            subtask.title = item.title
            subtask.is_complete = item.is_complete
            keep_ids.add(subtask.id)
            continue
        new_subtask = Task(
            user_id=current_user.id,
            parent_task_id=parent.id,
            title=item.title,
            is_complete=item.is_complete,
            priority=parent.priority,
            project_id=parent.project_id,
        )
        db.add(new_subtask)
        await db.flush()
        keep_ids.add(new_subtask.id)

    for subtask in parent.subtasks:
        if subtask.id not in keep_ids:
            await db.delete(subtask)

    await db.flush()
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == parent.id)
    )
    return result.scalar_one()


@router.post("/from-calendar-day", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_calendar_day(
    payload: CreateTaskFromCalendarDayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parsed_day = datetime.fromisoformat(payload.day_iso)
    deadline = datetime(parsed_day.year, parsed_day.month, parsed_day.day, 17, 0, 0)
    task = Task(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        deadline=deadline,
        priority=Priority.MEDIUM,
    )
    db.add(task)
    await db.flush()
    result = await db.execute(
        select(Task).options(selectinload(Task.subtasks)).where(Task.id == task.id)
    )
    return result.scalar_one()


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_owned_task(task_id: int, user_id: int, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.subtasks))
        .where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
