"""
Seed script for Planify — populates the SQLite database with demo data.

Run from the backend/ directory:
    python seed_data.py

Creates:
  - 1 demo user (demo@planify.app / demo1234)
  - 3 projects
  - 5 notes
  - 8 tasks (with 2 subtasks)
  - 4 calendar events
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Use relative imports via sys.path
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base
from app.models.models import User, Project, Note, Task, Event, Priority
from app.core.security import hash_password

DATABASE_URL = "sqlite+aiosqlite:///./planify.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Helpers ───────────────────────────────────────────────────────────────────
def now():
    return datetime.utcnow()

def future(days=0, hours=0, minutes=0):
    return now() + timedelta(days=days, hours=hours, minutes=minutes)

def past(days=0, hours=0, minutes=0):
    return now() - timedelta(days=days, hours=hours, minutes=minutes)


async def seed():
    # Create tables
    from sqlalchemy import create_engine
    sync_engine = create_engine("sqlite:///./planify.db")
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(User).where(User.email == "demo@planify.app"))
        if result.scalar_one_or_none():
            print("✅ Database already seeded. Skipping.")
            return

        print("🌱 Seeding Planify database...")

        # ── User ──────────────────────────────────────────────────────────────
        user = User(
            email="demo@planify.app",
            full_name="Julian Architect",
            hashed_password=hash_password("demo1234"),
            avatar_color="#435f92",
        )
        db.add(user)
        await db.flush()
        uid = user.id
        print(f"  ✓ User: {user.email} (id={uid})")

        # ── Projects ──────────────────────────────────────────────────────────
        p3 = Project(user_id=uid, name="Planify V2.0", color="#7c5831",
                     description="Product roadmap and feature tracking for the next major release")
        db.add(p3)
        await db.flush()
        p1 = Project(user_id=uid, parent_project_id=p3.id, name="Design System", color="#435f92",
                     description="Component library and design tokens for Planify V2")
        p2 = Project(user_id=uid, name="Home Renovation", color="#57634c",
                     description="Tracking tasks and notes for the house remodel project")
        db.add_all([p1, p2])
        await db.flush()
        print(f"  ✓ Projects: Design System, Home Renovation, Planify V2.0")

        # ── Notes ─────────────────────────────────────────────────────────────
        notes = [
            Note(user_id=uid, project_id=p3.id,
                 title="Architecture Framework v2",
                 content="<h3>The Hierarchy of Silence</h3><p>Noise in a UI is not just visual clutter; it's cognitive friction. By removing 1px borders, we allow the eye to glide across surfaces.</p><h3>II. Color as Temperature</h3><p>Every brand has a temperature. Our palette uses Secondary Greens to ground the workspace in calm.</p>",
                 color="#ffffff", folder="Personal Notes",
                 tags=["strategy", "design"], is_pinned=True),
            Note(user_id=uid, project_id=p1.id,
                 title="Quick Ideas: UI Motion",
                 content="The bounce should be subtle, mimicking physical weight. Spring animations should use a tension of 400 and friction of 25.",
                 color="#dae7ca", folder="Personal Notes",
                 tags=["design", "animation"], is_pinned=False),
            Note(user_id=uid,
                 title="Project Sanctuary Notes",
                 content="Exploring the intersections of mindful architecture and digital space. The goal is to create a workspace that feels expensive, calm, and hyper-focused.",
                 color="#a5c1fb", folder="Project X Hub",
                 tags=["strategy"], is_pinned=False),
            Note(user_id=uid, project_id=p2.id,
                 title="Kitchen Renovation Checklist",
                 content="- [ ] New countertops (quartz)\n- [ ] Cabinet repainting\n- [ ] Lighting upgrade\n- [ ] Appliance replacement",
                 color="#fdcb9c", folder="Personal Notes",
                 tags=["personal", "renovation"], is_pinned=False),
            Note(user_id=uid,
                 title="Reading List Q4",
                 content="1. Deep Work - Cal Newport\n2. The Design of Everyday Things\n3. Atomic Habits\n4. Shape Up - Basecamp",
                 color="#ffffff", folder="Inspiration",
                 tags=["personal", "learning"], is_pinned=False),
        ]
        db.add_all(notes)
        await db.flush()
        print(f"  ✓ Notes: {len(notes)} created")

        # ── Events ────────────────────────────────────────────────────────────
        events = [
            Event(user_id=uid, project_id=p1.id, title="System Review",
                  description="Quarterly design system review with the team",
                  color="#435f92",
                  start_time=future(hours=1), end_time=future(hours=2),
                  reminder_at=future(minutes=30)),
            Event(user_id=uid, project_id=p1.id, title="Design Workshop",
                  description="Interactive workshop on new component patterns",
                  color="#7c5831",
                  start_time=future(days=1, hours=14), end_time=future(days=1, hours=16),
                  reminder_at=future(days=1, hours=13)),
            Event(user_id=uid, project_id=p3.id, title="Weekly Sync with Product Team",
                  description="Regular product sync — review roadmap and blockers",
                  color="#435f92",
                  start_time=future(days=2, hours=11), end_time=future(days=2, hours=12),
                  reminder_at=future(days=2, hours=10)),
            Event(user_id=uid, title="Product Offsite",
                  description="Full team offsite for Q4 planning",
                  color="#57634c",
                  start_time=future(days=4), end_time=future(days=5),
                  all_day=True),
        ]
        db.add_all(events)
        await db.flush()
        print(f"  ✓ Events: {len(events)} created")

        # ── Tasks ─────────────────────────────────────────────────────────────
        t1 = Task(user_id=uid, project_id=p1.id,
                  title="Complete Brand Identity Refresh",
                  description="Finalize the color palette and typography for the new design system launch.",
                  priority=Priority.HIGH, tags=["work"],
                  deadline=future(days=1), reminder_at=future(hours=4), event_id=events[0].id)
        t2 = Task(user_id=uid,
                  title="Weekly Sync with Product Team",
                  description="Prepare agenda and sync notes.", priority=Priority.MEDIUM,
                  tags=["work", "management"],
                  deadline=future(hours=2), reminder_at=future(hours=1), event_id=events[2].id)
        t3 = Task(user_id=uid, project_id=p3.id,
                  title="Draft Content Strategy for Launch",
                  description="Outline the full go-to-market content calendar.",
                  priority=Priority.HIGH, tags=["work", "marketing"],
                  deadline=future(days=3), reminder_at=future(days=2, hours=18))
        t4 = Task(user_id=uid,
                  title="Weekly Meal Prep",
                  description="Prepare healthy lunches for the upcoming work week.",
                  priority=Priority.MEDIUM, tags=["personal"],
                  deadline=future(days=2))
        t5 = Task(user_id=uid,
                  title="Buy birthday gift for Sarah",
                  priority=Priority.LOW, tags=["personal"],
                  is_complete=True, deadline=past(days=1))
        t6 = Task(user_id=uid, project_id=p2.id,
                  title="Review architectural blueprints",
                  priority=Priority.MEDIUM, tags=["work"],
                  deadline=future(days=5))
        t7 = Task(user_id=uid,
                  title="Draft Q4 Strategic Proposal",
                  description="Deep work session for the annual strategic proposal document.",
                  priority=Priority.HIGH, tags=["work"],
                  deadline=future(days=7))
        t8 = Task(user_id=uid,
                  title="Process monthly invoices",
                  priority=Priority.LOW, tags=["admin"],
                  deadline=future(days=10))

        db.add_all([t1, t2, t3, t4, t5, t6, t7, t8])
        await db.flush()

        # Subtasks for t1
        sub1 = Task(user_id=uid, parent_task_id=t1.id,
                    title="Define typography scale", priority=Priority.MEDIUM,
                    is_complete=True)
        sub2 = Task(user_id=uid, parent_task_id=t1.id,
                    title="Audit current accessibility contrast", priority=Priority.HIGH)
        sub3 = Task(user_id=uid, parent_task_id=t1.id,
                    title="Export assets for development", priority=Priority.MEDIUM)
        db.add_all([sub1, sub2, sub3])
        await db.flush()
        print(f"  ✓ Tasks: 8 tasks + 3 subtasks created")

        await db.commit()
        print("\n✅ Seeding complete!")
        print("\n📋 Demo credentials:")
        print("   Email:    demo@planify.app")
        print("   Password: demo1234")


if __name__ == "__main__":
    asyncio.run(seed())
