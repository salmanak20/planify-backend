"""
Planify FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Docs at: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, notes, tasks, events, projects, dashboard, search, focus, reminders
from app.core.firebase_auth import validate_firebase_startup

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Planify API",
    description="All-in-one productivity backend: Notes, Tasks, Calendar, Projects",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow Flutter mobile app and any local dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize the database tables on app startup."""
    validate_firebase_startup()
    await init_db()


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Planify API is running 🚀"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(events.router)
app.include_router(projects.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(focus.router)
app.include_router(reminders.router)
