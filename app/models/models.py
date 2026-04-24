"""
SQLAlchemy ORM models for all Planify entities.
Schema: Users -> Notes, Tasks, Events, Projects (one-to-many)
Tasks can optionally link to Events and Projects can be nested.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Occupation(str, enum.Enum):
    STUDENT = "student"
    PROFESSIONAL = "professional"
    EMPLOYED = "employed"
    UNEMPLOYED = "unemployed"


# ── User ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(255), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)  # nullable for google sign in
    avatar_color = Column(String(20), default="#435f92")  # personalisation
    occupation = Column(SAEnum(Occupation), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="owner", cascade="all, delete-orphan")
    focus_sessions = relationship("FocusSession", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="owner", cascade="all, delete-orphan")


# ── Project ───────────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#435f92")  # hex color for project pill
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="projects")
    notes = relationship("Note", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    events = relationship("Event", back_populates="project")
    parent_project = relationship(
        "Project",
        back_populates="child_projects",
        remote_side=[id],
    )
    child_projects = relationship("Project", back_populates="parent_project")


# ── Note ──────────────────────────────────────────────────────────────────────
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False, default="Untitled Note")
    content = Column(Text, nullable=True)  # Rich text stored as HTML/Markdown
    color = Column(String(20), default="#ffffff")  # background color for card
    is_pinned = Column(Boolean, default=False)
    folder = Column(String(255), nullable=True)  # e.g. "Personal Notes", "Project X"
    tags = Column(JSON, default=list)  # ["strategy", "design", "draft"]
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="notes")
    project = relationship("Project", back_populates="notes")


# ── Task ──────────────────────────────────────────────────────────────────────
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    # Optional link to a calendar event (time-blocking)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)  # subtasks

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(SAEnum(Priority), default=Priority.MEDIUM, nullable=False)
    is_complete = Column(Boolean, default=False)
    tags = Column(JSON, default=list)  # ["work", "personal"]
    deadline = Column(DateTime, nullable=True)
    reminder_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    source_note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)
    source_note_line = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    event = relationship("Event", back_populates="linked_tasks", foreign_keys=[event_id])
    subtasks = relationship("Task", back_populates="parent_task", foreign_keys=[parent_task_id])
    parent_task = relationship("Task", back_populates="subtasks", remote_side="Task.id", foreign_keys=[parent_task_id])


# ── Event ─────────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    color = Column(String(20), default="#435f92")  # event block color
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reminder_at = Column(DateTime, nullable=True)
    all_day = Column(Boolean, default=False)
    repeat = Column(String(20), default="none", nullable=False)
    repeat_interval = Column(Integer, default=1, nullable=False)
    repeat_weekdays = Column(JSON, default=list)
    recurrence_end = Column(DateTime, nullable=True)
    skipped_occurrences = Column(JSON, default=list)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="events")
    project = relationship("Project", back_populates="events")
    linked_tasks = relationship("Task", back_populates="event", foreign_keys="Task.event_id")


# ── Focus Session ─────────────────────────────────────────────────────────────
class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="focus_sessions")
    project = relationship("Project")
    task = relationship("Task")


# ── Reminder (standalone quick reminders) ─────────────────────────────────────
class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)
    reminder_time = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False)
    repeat = Column(String(20), default="none", nullable=False)  # none, daily, weekly, monthly
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="reminders")
