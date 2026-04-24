-- Planify relational schema.
-- Primary target: PostgreSQL
-- Local development runtime uses SQLite through SQLAlchemy.

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    avatar_color VARCHAR(20) NOT NULL DEFAULT '#435f92',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(20) NOT NULL DEFAULT '#435f92',
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL DEFAULT 'Untitled Note',
    content TEXT,
    color VARCHAR(20) NOT NULL DEFAULT '#ffffff',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    folder VARCHAR(255),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    location VARCHAR(500),
    color VARCHAR(20) NOT NULL DEFAULT '#435f92',
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    reminder_at TIMESTAMP,
    all_day BOOLEAN NOT NULL DEFAULT FALSE,
    repeat VARCHAR(20) NOT NULL DEFAULT 'none',
    repeat_interval INTEGER NOT NULL DEFAULT 1,
    repeat_weekdays JSONB NOT NULL DEFAULT '[]'::jsonb,
    recurrence_end TIMESTAMP,
    skipped_occurrences JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_event_window CHECK (all_day = TRUE OR end_time > start_time),
    CONSTRAINT chk_event_reminder CHECK (reminder_at IS NULL OR reminder_at <= start_time)
);

CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');

CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    event_id BIGINT REFERENCES events(id) ON DELETE SET NULL,
    parent_task_id BIGINT REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority task_priority NOT NULL DEFAULT 'medium',
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    deadline TIMESTAMP,
    reminder_at TIMESTAMP,
    completed_at TIMESTAMP,
    source_note_id BIGINT REFERENCES notes(id) ON DELETE SET NULL,
    source_note_line TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_task_reminder CHECK (deadline IS NULL OR reminder_at IS NULL OR reminder_at <= deadline)
);

CREATE TABLE focus_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    task_id BIGINT REFERENCES tasks(id) ON DELETE SET NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_seconds INTEGER NOT NULL,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_focus_duration CHECK (duration_seconds > 0)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_project_id ON notes(project_id);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_project_id ON events(project_id);
CREATE INDEX idx_events_start_time ON events(start_time);
CREATE INDEX idx_focus_sessions_user_id ON focus_sessions(user_id);
