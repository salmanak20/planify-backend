"""
Projects router — CRUD + nested resource endpoints (tasks, notes in project).
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import User, Project, Task, Note
from app.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.dashboard import ProjectAnalyticsResponse
from app.schemas.tasks import TaskResponse
from app.schemas.notes import NoteResponse
from app.core.security import get_current_user
from app.services.ownership import validate_project_parent
from app.services.insights import get_project_analytics

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id, Project.is_archived == False)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await validate_project_parent(
        db,
        user_id=current_user.id,
        parent_project_id=payload.parent_project_id,
    )
    project = Project(**payload.model_dump(), user_id=current_user.id)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_project(project_id, current_user.id, db)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    if "parent_project_id" in update_data:
        await validate_project_parent(
            db,
            user_id=current_user.id,
            parent_project_id=update_data["parent_project_id"],
            current_project_id=project.id,
        )
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    await db.delete(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a project instead of deleting it."""
    project = await _get_owned_project(project_id, current_user.id, db)
    project.is_archived = True
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
async def get_project_tasks(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all tasks belonging to a specific project."""
    await _get_owned_project(project_id, current_user.id, db)
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.subtasks))
        .where(Task.project_id == project_id, Task.user_id == current_user.id, Task.is_archived == False)
        .order_by(Task.is_complete.asc(), Task.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}/notes", response_model=List[NoteResponse])
async def get_project_notes(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all notes belonging to a specific project."""
    await _get_owned_project(project_id, current_user.id, db)
    result = await db.execute(
        select(Note)
        .where(Note.project_id == project_id, Note.user_id == current_user.id, Note.is_archived == False)
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}/analytics", response_model=ProjectAnalyticsResponse)
async def project_analytics(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_project(project_id, current_user.id, db)
    return await get_project_analytics(db, current_user.id, project_id)


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_owned_project(project_id: int, user_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
