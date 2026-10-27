"""
database.py - SQLite storage for users, assessments, chat messages and login events.

Tables:
  users          : accounts (password is stored HASHED, never as plain text)
  assessments    : every guidance result a user generated
  chat_messages  : follow-up chat, linked to one assessment
  login_events   : signup / login / failed / locked / logout records (for the admin)
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

# The .db file lives in the project root (next to app.py).
DB_PATH = Path(
    os.getenv("MEDIGUIDE_DB", Path(__file__).resolve().parent.parent / "mediguide.db")
)


def now_iso() -> str:
    """Current time as text, e.g. 2026-10-27T15:20:05 (the app replaces 'T' with a space)."""
    return datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Tiny helpers so every function below stays short
# --------------------------------------------------------------------------
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # lets "ON DELETE CASCADE" work
    return conn


def _all(sql: str, params=()) -> list:
    with closing(_connect()) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _one(sql: str, params=()):
    rows = _all(sql, params)
    return rows[0] if rows else None


def _exec(sql: str, params=()) -> int:
    """Run an INSERT/UPDATE/DELETE, commit, and return the new row id."""
    with closing(_connect()) as conn:
        with conn:  # commits on success, rolls back on error
            return conn.execute(sql, params).lastrowid


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user',
    created_at      TEXT NOT NULL,
    last_login      TEXT,
    login_count     INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT
);

CREATE TABLE IF NOT EXISTS assessments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TEXT NOT NULL,
    symptoms     TEXT,
    severity     INTEGER,
    urgency      TEXT,
    model_name   TEXT,
    inputs_json  TEXT,
    result_json  TEXT,
    narrative    TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    username   TEXT,
    event      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_db():
    """Create the tables (if missing) and make sure an admin account exists."""
    with closing(_connect()) as conn:
        with conn:
            conn.executescript(SCHEMA)
    _ensure_admin()


def _ensure_admin():
    """
    Create the first admin account if it does not exist.
    Set ADMIN_USERNAME / ADMIN_PASSWORD in .env to choose your own.
    """
    from src import auth  # imported here to avoid a circular import

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
    if get_user_by_username(username) is None:
        create_user(
            username, "Administrator", "admin@example.com",
            auth.hash_password(password), role="admin",
        )


# --------------------------------------------------------------------------
# Users and login events (used by auth.py)
# --------------------------------------------------------------------------
def create_user(username, full_name, email, password_hash, role="user") -> int:
    return _exec(
        "INSERT INTO users (username, full_name, email, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, full_name, email, password_hash, role, now_iso()),
    )


def get_user_by_username(username: str):
    return _one("SELECT * FROM users WHERE username = ?", (username,))


def mark_login_success(user_id: int):
    _exec(
        "UPDATE users SET last_login = ?, login_count = login_count + 1, "
        "failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (now_iso(), user_id),
    )


def register_failed_attempt(user_id: int, max_attempts: int, lock_minutes: int) -> bool:
    """Count a wrong password. Returns True if the account just got locked."""
    user = _one("SELECT failed_attempts FROM users WHERE id = ?", (user_id,))
    attempts = (user["failed_attempts"] if user else 0) + 1
    if attempts >= max_attempts:
        until = datetime.now().timestamp() + lock_minutes * 60
        locked_until = datetime.fromtimestamp(until).isoformat(timespec="seconds")
        _exec(
            "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?",
            (locked_until, user_id),
        )
        return True
    _exec("UPDATE users SET failed_attempts = ? WHERE id = ?", (attempts, user_id))
    return False


def log_event(username: str, event: str, user_id=None):
    _exec(
        "INSERT INTO login_events (user_id, username, event, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, event, now_iso()),
    )


# --------------------------------------------------------------------------
# Assessments
# --------------------------------------------------------------------------
def _symptom_text(value) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value or "")


def save_assessment(user_id: int, inputs: dict, parsed: dict, model_name: str) -> int:
    return _exec(
        "INSERT INTO assessments (user_id, created_at, symptoms, severity, urgency, "
        "model_name, inputs_json, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            now_iso(),
            _symptom_text(inputs.get("symptoms")),
            inputs.get("severity"),
            parsed.get("urgency_level"),
            model_name,
            json.dumps(inputs, ensure_ascii=False, default=str),
            json.dumps(parsed, ensure_ascii=False, default=str),
        ),
    )


def _row_to_assessment(row: dict) -> dict:
    """Turn a database row into the dict the UI expects."""
    inputs = json.loads(row["inputs_json"] or "{}")
    parsed = json.loads(row["result_json"]) if row["result_json"] else None
    a = dict(inputs)  # age, gender, duration, language, ... are available directly
    a.update(
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "urgency": row["urgency"],
            "model_name": row["model_name"],
            "narrative": row["narrative"],
            "parsed": parsed,
            "inputs": inputs,
        }
    )
    a.setdefault("symptoms", row["symptoms"])
    a.setdefault("severity", row["severity"])
    return a


def get_assessment(assessment_id: int, user_id: int):
    """Returns the assessment ONLY if it belongs to user_id (privacy)."""
    row = _one(
        "SELECT * FROM assessments WHERE id = ? AND user_id = ?", (assessment_id, user_id)
    )
    return _row_to_assessment(row) if row else None


def list_assessments(user_id: int) -> list:
    return _all(
        "SELECT id, created_at, symptoms, severity, urgency FROM assessments "
        "WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )


def update_narrative(assessment_id: int, text: str):
    _exec("UPDATE assessments SET narrative = ? WHERE id = ?", (text, assessment_id))


def delete_assessment(assessment_id: int, user_id: int):
    # The chat messages are removed automatically (ON DELETE CASCADE).
    _exec("DELETE FROM assessments WHERE id = ? AND user_id = ?", (assessment_id, user_id))


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
def get_chat_messages(assessment_id: int) -> list:
    return _all(
        "SELECT role, content FROM chat_messages WHERE assessment_id = ? ORDER BY id",
        (assessment_id,),
    )


def add_chat_message(assessment_id: int, role: str, content: str):
    _exec(
        "INSERT INTO chat_messages (assessment_id, role, content, created_at) "
        "VALUES (?, ?, ?, ?)",
        (assessment_id, role, content, now_iso()),
    )


# --------------------------------------------------------------------------
# Statistics (analytics page and admin panel)
# --------------------------------------------------------------------------
def urgency_counts(user_id=None) -> dict:
    """{'LOW': 2, 'HIGH': 1, ...}. Pass None to count everyone (admin overview)."""
    if user_id is None:
        rows = _all(
            "SELECT urgency, COUNT(*) AS n FROM assessments GROUP BY urgency"
        )
    else:
        rows = _all(
            "SELECT urgency, COUNT(*) AS n FROM assessments WHERE user_id = ? GROUP BY urgency",
            (user_id,),
        )
    return {r["urgency"]: r["n"] for r in rows if r["urgency"]}


def totals() -> dict:
    return {
        "users": _one("SELECT COUNT(*) AS n FROM users")["n"],
        "logins": _one("SELECT COUNT(*) AS n FROM login_events WHERE event = 'login'")["n"],
        "assessments": _one("SELECT COUNT(*) AS n FROM assessments")["n"],
    }


def list_users() -> list:
    """Accounts with counts only - NO medical details (privacy)."""
    return _all(
        "SELECT u.id, u.username, u.full_name, u.email, u.role, u.created_at, "
        "u.last_login, u.login_count, "
        "(SELECT COUNT(*) FROM assessments a WHERE a.user_id = u.id) AS assessments "
        "FROM users u ORDER BY u.id"
    )


def recent_events(limit: int = 200) -> list:
    return _all(
        "SELECT username, event, created_at FROM login_events ORDER BY id DESC LIMIT ?",
        (limit,),
    )