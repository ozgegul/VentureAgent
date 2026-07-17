"""SQLite database helpers for VentureAgent."""

from __future__ import annotations

import json
import secrets
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


def init_db() -> None:
    """Create database tables when they do not exist."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS idea_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            mentor_problem_clarity INTEGER,
            mentor_market_potential INTEGER,
            mentor_revenue_potential INTEGER,
            mentor_mvp_feasibility INTEGER,
            mentor_overall_score INTEGER,
            mentor_notes TEXT,
            public_token TEXT,
            session_id TEXT,
            public_hidden_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_columns(
        db,
        "idea_analyses",
        {
            "mentor_problem_clarity": "INTEGER",
            "mentor_market_potential": "INTEGER",
            "mentor_revenue_potential": "INTEGER",
            "mentor_mvp_feasibility": "INTEGER",
            "mentor_overall_score": "INTEGER",
            "mentor_notes": "TEXT",
            "public_token": "TEXT",
            "session_id": "TEXT",
            "public_hidden_at": "TEXT",
        },
    )
    db.commit()


def _ensure_columns(db: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    """Add missing columns for lightweight SQLite migrations."""
    existing_columns = {
        row["name"]
        for row in db.execute(f"PRAGMA table_info({table})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")


def init_app(app) -> None:
    """Register database lifecycle hooks and initialize schema."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def save_idea_analysis(
    *,
    idea: str,
    problem: str,
    target_audience: str,
    sector: str,
    signal,
    venture_score,
    ai_analysis: str | None,
    session_id: str | None = None,
) -> int:
    """Persist an idea analysis and return the inserted row id."""
    public_token = secrets.token_urlsafe(24)
    cursor = get_db().execute(
        """
        INSERT INTO idea_analyses (
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
            public_token,
            session_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
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
            public_token,
            session_id,
        ),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def list_session_idea_analyses(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return saved analyses that belong to one browser session."""
    rows = get_db().execute(
        """
        SELECT
            id,
            idea,
            sector,
            venture_score,
            risk_level,
            readiness_label,
            public_token,
            created_at
        FROM idea_analyses
        WHERE session_id = ? AND public_hidden_at IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    return [dict(row) for row in rows.fetchall()]


def list_idea_analyses(limit: int = 25) -> list[dict[str, Any]]:
    """Return the latest saved idea analyses."""
    rows = get_db().execute(
        """
        SELECT
            id,
            idea,
            sector,
            venture_score,
            risk_level,
            readiness_label,
            ai_analysis,
            created_at
        FROM idea_analyses
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in rows.fetchall()]


def save_chat_message(*, session_id: str, role: str, content: str) -> int:
    """Persist one chat message and return the inserted row id."""
    cursor = get_db().execute(
        """
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (?, ?, ?)
        """,
        (session_id, role, content),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def list_chat_messages(limit: int = 100, role: str | None = None) -> list[dict[str, Any]]:
    """Return the latest saved chat messages."""
    if role:
        rows = get_db().execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM chat_messages
            WHERE role = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (role, limit),
        )
    else:
        rows = get_db().execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM chat_messages
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )

    return [dict(row) for row in rows.fetchall()]


def get_admin_metrics() -> dict[str, int]:
    """Return simple admin counters."""
    db = get_db()
    row = db.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM idea_analyses) AS total_ideas,
            (SELECT COUNT(*) FROM chat_messages WHERE role = 'user') AS total_user_messages,
            (SELECT COUNT(DISTINCT session_id) FROM chat_messages) AS total_chat_sessions
        """
    ).fetchone()
    return dict(row)


def get_idea_analysis(analysis_id: int) -> dict[str, Any] | None:
    """Return one saved idea analysis with all stored fields."""
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
            mentor_problem_clarity,
            mentor_market_potential,
            mentor_revenue_potential,
            mentor_mvp_feasibility,
            mentor_overall_score,
            mentor_notes,
            created_at
        FROM idea_analyses
        WHERE id = ?
        """,
        (analysis_id,),
    ).fetchone()

    if row is None:
        return None

    analysis = dict(row)
    analysis["recommendations"] = json.loads(analysis["recommendations"])
    return analysis


def get_public_idea_analysis(public_token: str, session_id: str) -> dict[str, Any] | None:
    """Return one analysis when token and browser session match."""
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
            mentor_problem_clarity,
            mentor_market_potential,
            mentor_revenue_potential,
            mentor_mvp_feasibility,
            mentor_overall_score,
            mentor_notes,
            public_token,
            public_hidden_at,
            created_at
        FROM idea_analyses
        WHERE public_token = ? AND session_id = ? AND public_hidden_at IS NULL
        """,
        (public_token, session_id),
    ).fetchone()

    if row is None:
        return None

    analysis = dict(row)
    analysis["recommendations"] = json.loads(analysis["recommendations"])
    return analysis


def delete_idea_analysis(analysis_id: int) -> None:
    """Delete one saved idea analysis."""
    get_db().execute("DELETE FROM idea_analyses WHERE id = ?", (analysis_id,))
    get_db().commit()


def hide_public_idea_analysis(analysis_id: int) -> None:
    """Hide one analysis from the public user's history without removing admin data."""
    get_db().execute(
        "UPDATE idea_analyses SET public_hidden_at = CURRENT_TIMESTAMP WHERE id = ?",
        (analysis_id,),
    )
    get_db().commit()


def save_mentor_evaluation(
    *,
    analysis_id: int,
    problem_clarity: int,
    market_potential: int,
    revenue_potential: int,
    mvp_feasibility: int,
    overall_score: int,
    notes: str,
) -> None:
    """Save mentor labels for future model training."""
    get_db().execute(
        """
        UPDATE idea_analyses
        SET
            mentor_problem_clarity = ?,
            mentor_market_potential = ?,
            mentor_revenue_potential = ?,
            mentor_mvp_feasibility = ?,
            mentor_overall_score = ?,
            mentor_notes = ?
        WHERE id = ?
        """,
        (
            _normalize_label(problem_clarity),
            _normalize_label(market_potential),
            _normalize_label(revenue_potential),
            _normalize_label(mvp_feasibility),
            _normalize_label(overall_score),
            notes.strip(),
            analysis_id,
        ),
    )
    get_db().commit()


def _normalize_label(value: int) -> int:
    """Keep mentor labels in the 1-5 range."""
    return max(1, min(5, int(value)))


def get_dashboard_metrics() -> dict[str, Any]:
    """Return aggregate metrics for the data science dashboard."""
    db = get_db()
    summary = db.execute(
        """
        SELECT
            COUNT(*) AS total_analyses,
            ROUND(AVG(venture_score), 2) AS average_score,
            MAX(venture_score) AS best_score,
            MIN(venture_score) AS lowest_score,
            COUNT(mentor_overall_score) AS labeled_analyses,
            ROUND(AVG(mentor_overall_score), 2) AS average_mentor_score
        FROM idea_analyses
        """
    ).fetchone()

    risk_rows = db.execute(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM idea_analyses
        GROUP BY risk_level
        ORDER BY count DESC
        """
    ).fetchall()

    sector_rows = db.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(sector), ''), 'Belirtilmedi') AS sector, COUNT(*) AS count
        FROM idea_analyses
        GROUP BY COALESCE(NULLIF(TRIM(sector), ''), 'Belirtilmedi')
        ORDER BY count DESC, sector ASC
        LIMIT 6
        """
    ).fetchall()

    top_rows = db.execute(
        """
        SELECT id, idea, sector, venture_score, risk_level, readiness_label
        FROM idea_analyses
        ORDER BY venture_score DESC, id DESC
        LIMIT 5
        """
    ).fetchall()

    return {
        "summary": dict(summary),
        "risk_distribution": [dict(row) for row in risk_rows],
        "sector_distribution": [dict(row) for row in sector_rows],
        "top_ideas": [dict(row) for row in top_rows],
    }
