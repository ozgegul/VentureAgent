"""SQLite database helpers for VentureAgent."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from flask import current_app, g


def get_database_path() -> Path:
    """Return the configured SQLite database path."""
    return Path(current_app.instance_path) / "ventureagent.sqlite3"


def get_db() -> sqlite3.Connection:
    """Open one SQLite connection per request."""
    if "db" not in g:
        db_path = get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        g.db = connection

    return g.db


def close_db(_: Exception | None = None) -> None:
    """Close the request database connection."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def _table_has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if the given table already has the given column."""
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def init_db() -> None:
    """Create database tables when they do not exist, and run light migrations."""
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'free',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS idea_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            idea TEXT NOT NULL,
            problem TEXT NOT NULL,
            target_audience TEXT,
            sector TEXT,
            problem_severity INTEGER NOT NULL,
            target_audience_clarity INTEGER NOT NULL,
            competition_intensity INTEGER NOT NULL,
            monetization_clarity INTEGER NOT NULL,
            venture_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            readiness_label TEXT NOT NULL,
            recommendations TEXT NOT NULL,
            ai_analysis TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    # Migration: older databases were created before user_id existed.
    if not _table_has_column(db, "idea_analyses", "user_id"):
        db.execute("ALTER TABLE idea_analyses ADD COLUMN user_id INTEGER")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS module_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            idea TEXT NOT NULL,
            input_data TEXT,
            result_data TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    db.commit()


def init_app(app) -> None:
    """Register database lifecycle hooks and initialize schema."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

ROLES = ("free", "pro", "admin")


def create_user(*, name: str, email: str, password_hash: str, role: str = "free") -> int:
    """Insert a new user and return the inserted row id."""
    cursor = get_db().execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, email.lower().strip(), password_hash, role),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Return one user by (case-insensitive) email, or None."""
    row = get_db().execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Return one user by id, or None."""
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def list_users(limit: int = 200) -> list[dict[str, Any]]:
    """Return all users, most recent first (used by the admin panel)."""
    rows = get_db().execute(
        "SELECT id, name, email, role, is_active, created_at FROM users "
        "ORDER BY created_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def update_user_role(user_id: int, role: str) -> None:
    """Change a user's role. Caller is responsible for validating `role`."""
    if role not in ROLES:
        raise ValueError(f"Geçersiz rol: {role}")
    get_db().execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    get_db().commit()


def set_user_active(user_id: int, is_active: bool) -> None:
    """Activate or deactivate (soft-ban) a user account."""
    get_db().execute(
        "UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id)
    )
    get_db().commit()


# ---------------------------------------------------------------------------
# Generic module results (SWOT, rakip, gelir, roadmap, yatırımcı, pitch, kanban)
# ---------------------------------------------------------------------------


def save_module_result(
    *, user_id: int, module: str, idea: str, input_data: dict[str, Any] | None, result_data: Any
) -> int:
    """Persist one AI module result tied to a user."""
    cursor = get_db().execute(
        """
        INSERT INTO module_results (user_id, module, idea, input_data, result_data)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            module,
            idea,
            json.dumps(input_data, ensure_ascii=False) if input_data is not None else None,
            json.dumps(result_data, ensure_ascii=False),
        ),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def list_module_results(user_id: int, module: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return saved module results for one user, newest first."""
    if module:
        rows = get_db().execute(
            """
            SELECT id, module, idea, created_at FROM module_results
            WHERE user_id = ? AND module = ?
            ORDER BY created_at DESC, id DESC LIMIT ?
            """,
            (user_id, module, limit),
        ).fetchall()
    else:
        rows = get_db().execute(
            """
            SELECT id, module, idea, created_at FROM module_results
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_module_result(result_id: int, user_id: int) -> dict[str, Any] | None:
    """Return one module result, scoped to its owning user."""
    row = get_db().execute(
        "SELECT * FROM module_results WHERE id = ? AND user_id = ?", (result_id, user_id)
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["result_data"] = json.loads(result["result_data"])
    result["input_data"] = json.loads(result["input_data"]) if result["input_data"] else None
    return result


def delete_module_result(result_id: int, user_id: int) -> None:
    """Delete one module result, scoped to its owning user."""
    get_db().execute(
        "DELETE FROM module_results WHERE id = ? AND user_id = ?", (result_id, user_id)
    )
    get_db().commit()


def save_idea_analysis(
    *,
    user_id: int | None,
    idea: str,
    problem: str,
    target_audience: str,
    sector: str,
    signal,
    venture_score,
    ai_analysis: str | None,
) -> int:
    """Persist an idea analysis and return the inserted row id."""
    cursor = get_db().execute(
        """
        INSERT INTO idea_analyses (
            user_id,
            idea,
            problem,
            target_audience,
            sector,
            problem_severity,
            target_audience_clarity,
            competition_intensity,
            monetization_clarity,
            venture_score,
            risk_level,
            readiness_label,
            recommendations,
            ai_analysis
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            idea,
            problem,
            target_audience,
            sector,
            signal.problem_severity,
            signal.target_audience_clarity,
            signal.competition_intensity,
            signal.monetization_clarity,
            venture_score.score,
            venture_score.risk_level,
            venture_score.readiness_label,
            json.dumps(venture_score.recommendations, ensure_ascii=False),
            ai_analysis,
        ),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def list_idea_analyses(user_id: int, limit: int = 25) -> list[dict[str, Any]]:
    """Return the latest saved idea analyses for one user."""
    rows = get_db().execute(
        """
        SELECT
            id,
            idea,
            sector,
            venture_score,
            risk_level,
            readiness_label,
            created_at
        FROM idea_analyses
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    return [dict(row) for row in rows.fetchall()]


def get_idea_analysis(analysis_id: int, user_id: int) -> dict[str, Any] | None:
    """Return one saved idea analysis with all stored fields, scoped to its owner."""
    row = get_db().execute(
        """
        SELECT
            id,
            idea,
            problem,
            target_audience,
            sector,
            problem_severity,
            target_audience_clarity,
            competition_intensity,
            monetization_clarity,
            venture_score,
            risk_level,
            readiness_label,
            recommendations,
            ai_analysis,
            created_at
        FROM idea_analyses
        WHERE id = ? AND user_id = ?
        """,
        (analysis_id, user_id),
    ).fetchone()

    if row is None:
        return None

    analysis = dict(row)
    analysis["recommendations"] = json.loads(analysis["recommendations"])
    return analysis


def delete_idea_analysis(analysis_id: int, user_id: int) -> None:
    """Delete one saved idea analysis, scoped to its owner."""
    get_db().execute(
        "DELETE FROM idea_analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)
    )
    get_db().commit()


def get_dashboard_metrics(user_id: int) -> dict[str, Any]:
    """Return aggregate metrics for one user's data science dashboard."""
    db = get_db()
    summary = db.execute(
        """
        SELECT
            COUNT(*) AS total_analyses,
            ROUND(AVG(venture_score), 2) AS average_score,
            MAX(venture_score) AS best_score,
            MIN(venture_score) AS lowest_score
        FROM idea_analyses
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    risk_rows = db.execute(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM idea_analyses
        WHERE user_id = ?
        GROUP BY risk_level
        ORDER BY count DESC
        """,
        (user_id,),
    ).fetchall()

    sector_rows = db.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(sector), ''), 'Belirtilmedi') AS sector, COUNT(*) AS count
        FROM idea_analyses
        WHERE user_id = ?
        GROUP BY COALESCE(NULLIF(TRIM(sector), ''), 'Belirtilmedi')
        ORDER BY count DESC, sector ASC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()

    top_rows = db.execute(
        """
        SELECT id, idea, sector, venture_score, risk_level, readiness_label
        FROM idea_analyses
        WHERE user_id = ?
        ORDER BY venture_score DESC, id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    return {
        "summary": dict(summary),
        "risk_distribution": [dict(row) for row in risk_rows],
        "sector_distribution": [dict(row) for row in sector_rows],
        "top_ideas": [dict(row) for row in top_rows],
    }


def get_platform_metrics() -> dict[str, Any]:
    """Return site-wide aggregate metrics for the admin panel (all users)."""
    db = get_db()
    user_summary = db.execute(
        """
        SELECT
            COUNT(*) AS total_users,
            SUM(CASE WHEN role = 'pro' THEN 1 ELSE 0 END) AS pro_users,
            SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) AS admin_users,
            SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive_users
        FROM users
        """
    ).fetchone()

    analysis_summary = db.execute(
        """
        SELECT
            COUNT(*) AS total_analyses,
            ROUND(AVG(venture_score), 2) AS average_score
        FROM idea_analyses
        """
    ).fetchone()

    module_rows = db.execute(
        """
        SELECT module, COUNT(*) AS count
        FROM module_results
        GROUP BY module
        ORDER BY count DESC
        """
    ).fetchall()

    return {
        "users": dict(user_summary),
        "analyses": dict(analysis_summary),
        "module_usage": [dict(row) for row in module_rows],
    }
