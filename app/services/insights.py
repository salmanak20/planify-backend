from datetime import datetime, timedelta
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Task, Event, Note, Project
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardTaskItem,
    DashboardEventItem,
    DashboardNoteItem,
    ActiveFocusSession,
    ProjectAnalyticsResponse,
    ProjectActivityItem,
)
from app.schemas.search import GlobalSearchResponse, SearchItem


async def get_dashboard_summary(db: AsyncSession, user_id: int) -> DashboardSummaryResponse:
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    day_end = day_start + timedelta(days=1)

    task_rows = (
        await db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.is_archived == False,
                Task.parent_task_id.is_(None),
                Task.deadline.is_not(None),
                Task.deadline >= day_start,
                Task.deadline < day_end,
            )
            .order_by(Task.is_complete.asc(), Task.deadline.asc())
            .limit(8)
        )
    ).scalars().all()

    event_rows = (
        await db.execute(
            select(Event)
            .where(Event.user_id == user_id, Event.start_time >= now, Event.is_archived == False)
            .order_by(Event.start_time.asc())
            .limit(5)
        )
    ).scalars().all()

    note_rows = (
        await db.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.is_archived == False)
            .order_by(Note.updated_at.desc())
            .limit(5)
        )
    ).scalars().all()

    return DashboardSummaryResponse(
        today_tasks=[
            DashboardTaskItem(
                id=item.id,
                title=item.title,
                deadline=item.deadline,
                priority=item.priority.value if hasattr(item.priority, "value") else str(item.priority),
                is_complete=item.is_complete,
            )
            for item in task_rows
        ],
        upcoming_events=[
            DashboardEventItem(
                id=item.id,
                title=item.title,
                start_time=item.start_time,
                end_time=item.end_time,
                all_day=item.all_day,
            )
            for item in event_rows
        ],
        active_focus_session=ActiveFocusSession(),
        recent_notes=[
            DashboardNoteItem(
                id=item.id,
                title=item.title,
                updated_at=item.updated_at,
                is_pinned=item.is_pinned,
            )
            for item in note_rows
        ],
    )


async def get_project_analytics(db: AsyncSession, user_id: int, project_id: int) -> ProjectAnalyticsResponse:
    now = datetime.utcnow()
    task_rows = (
        await db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.is_archived == False,
                Task.project_id == project_id,
                Task.parent_task_id.is_(None),
            )
        )
    ).scalars().all()
    total = len(task_rows)
    completed = len([item for item in task_rows if item.is_complete])
    overdue = len([item for item in task_rows if not item.is_complete and item.deadline and item.deadline < now])
    progress = (completed / total * 100.0) if total else 0.0

    note_rows = (
        await db.execute(
            select(Note).where(Note.user_id == user_id, Note.project_id == project_id, Note.is_archived == False).order_by(Note.updated_at.desc()).limit(4)
        )
    ).scalars().all()

    event_rows = (
        await db.execute(
            select(Event).where(Event.user_id == user_id, Event.project_id == project_id, Event.is_archived == False).order_by(Event.updated_at.desc()).limit(4)
        )
    ).scalars().all()

    activity = [
        *[
            ProjectActivityItem(item_type="task", item_id=item.id, title=item.title, timestamp=item.updated_at)
            for item in sorted(task_rows, key=lambda x: x.updated_at, reverse=True)[:4]
        ],
        *[
            ProjectActivityItem(item_type="note", item_id=item.id, title=item.title, timestamp=item.updated_at)
            for item in note_rows
        ],
        *[
            ProjectActivityItem(item_type="event", item_id=item.id, title=item.title, timestamp=item.updated_at)
            for item in event_rows
        ],
    ]
    activity.sort(key=lambda x: x.timestamp, reverse=True)
    return ProjectAnalyticsResponse(
        project_id=project_id,
        progress_percent=round(progress, 2),
        completed_tasks=completed,
        overdue_items=overdue,
        recent_activity=activity[:8],
    )


async def global_search(db: AsyncSession, user_id: int, query: str) -> GlobalSearchResponse:
    like = f"%{query}%"
    tasks = (
        await db.execute(select(Task).where(Task.user_id == user_id, Task.is_archived == False, or_(Task.title.ilike(like), Task.description.ilike(like))).limit(10))
    ).scalars().all()
    notes = (
        await db.execute(select(Note).where(Note.user_id == user_id, Note.is_archived == False, or_(Note.title.ilike(like), Note.content.ilike(like))).limit(10))
    ).scalars().all()
    events = (
        await db.execute(select(Event).where(Event.user_id == user_id, Event.is_archived == False, or_(Event.title.ilike(like), Event.description.ilike(like))).limit(10))
    ).scalars().all()
    projects = (
        await db.execute(select(Project).where(Project.user_id == user_id, Project.is_archived == False, or_(Project.name.ilike(like), Project.description.ilike(like))).limit(10))
    ).scalars().all()

    return GlobalSearchResponse(
        tasks=[SearchItem(id=item.id, type="task", title=item.title, subtitle=item.description, project_id=item.project_id) for item in tasks],
        notes=[SearchItem(id=item.id, type="note", title=item.title, subtitle=item.content, project_id=item.project_id) for item in notes],
        events=[SearchItem(id=item.id, type="event", title=item.title, subtitle=item.description, project_id=item.project_id) for item in events],
        projects=[SearchItem(id=item.id, type="project", title=item.name, subtitle=item.description, project_id=item.id) for item in projects],
    )
