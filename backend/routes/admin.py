"""Admin routes for reviewing user input."""

import os
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Blueprint, redirect, render_template, request, session, url_for

from backend.database import get_admin_metrics, list_chat_messages, list_idea_analyses

admin_bp = Blueprint("admin", __name__, template_folder="../../frontend/templates")


@admin_bp.route("/", methods=["GET", "POST"])
def admin_page():
    """Show recent user submissions and chat messages."""
    password = _get_admin_password()
    error = None

    if not password:
        return render_template(
            "admin_login.html",
            error="ADMIN_PASSWORD tanımlı değil. .env dosyasına admin şifresi eklenmeli.",
        )

    if not session.get("admin_authenticated"):
        if request.method == "POST":
            if request.form.get("password", "") == password:
                session["admin_authenticated"] = True
                return redirect(url_for("admin.admin_page"))
            error = "Şifre hatalı."

        return render_template("admin_login.html", error=error)

    return render_template(
        "admin.html",
        metrics=get_admin_metrics(),
        chat_messages=list_chat_messages(limit=80, role="user"),
        analyses=list_idea_analyses(limit=30),
    )


@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    """Clear the admin session."""
    session.pop("admin_authenticated", None)
    return redirect(url_for("admin.admin_page"))


def _get_admin_password() -> str:
    """Read admin password from the project .env file."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path, override=True)
    return os.environ.get("ADMIN_PASSWORD", "").strip()


def admin_required(view):
    """Redirect non-admin users to the admin login page."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin.admin_page"))
        return view(*args, **kwargs)

    return wrapped_view
