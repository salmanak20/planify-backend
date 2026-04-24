"""Validation helpers for user-owned entities and nested relationships."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Event, Project, Task


async def require_project(
    db: AsyncSession,
    *,
    user_id: int,
    project_id: int,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def require_event(
    db: AsyncSession,
    *,
    user_id: int,
    event_id: int,
) -> Event:
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.user_id == user_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return event


async def require_task(
    db: AsyncSession,
    *,
    user_id: int,
    task_id: int,
) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


async def validate_project_assignment(
    db: AsyncSession,
    *,
    user_id: int,
    project_id: int | None,
) -> None:
    if project_id is None:
        return
    await require_project(db, user_id=user_id, project_id=project_id)


async def validate_project_parent(
    db: AsyncSession,
    *,
    user_id: int,
    parent_project_id: int | None,
    current_project_id: int | None = None,
) -> None:
    if parent_project_id is None:
        return

    if current_project_id is not None and parent_project_id == current_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project cannot be its own parent",
        )

    parent = await require_project(db, user_id=user_id, project_id=parent_project_id)
    seen_ids = set()
    cursor = parent

    while cursor is not None:
        if cursor.id in seen_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project nesting contains a cycle",
            )
        if current_project_id is not None and cursor.id == current_project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project nesting cannot create a cycle",
            )
        seen_ids.add(cursor.id)
        if cursor.parent_project_id is None:
            break
        cursor = await require_project(
            db,
            user_id=user_id,
            project_id=cursor.parent_project_id,
        )


async def validate_task_links(
    db: AsyncSession,
    *,
    user_id: int,
    project_id: int | None,
    event_id: int | None,
    parent_task_id: int | None,
    current_task_id: int | None = None,
) -> None:
    if project_id is not None:
        await require_project(db, user_id=user_id, project_id=project_id)

    if event_id is not None:
        event = await require_event(db, user_id=user_id, event_id=event_id)
        if project_id is not None and event.project_id is not None and event.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Linked event belongs to a different project",
            )

    if parent_task_id is None:
        return

    if current_task_id is not None and parent_task_id == current_task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot be its own parent",
        )

    parent = await require_task(db, user_id=user_id, task_id=parent_task_id)
    if project_id is not None and parent.project_id not in {None, project_id}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent task belongs to a different project",
        )

    seen_ids = set()
    cursor = parent
    while cursor is not None:
        if cursor.id in seen_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task nesting contains a cycle",
            )
        if current_task_id is not None and cursor.id == current_task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task nesting cannot create a cycle",
            )
        seen_ids.add(cursor.id)
        if cursor.parent_task_id is None:
            break
        cursor = await require_task(db, user_id=user_id, task_id=cursor.parent_task_id)
