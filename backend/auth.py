"""Authentication helpers: session-based login, role checks, decorators.

Basitlik için Flask-Login gibi bir bağımlılık eklemek yerine, mevcut
`session` (çerez) mekanizması ve `werkzeug.security` şifre hash'i
kullanılıyor. Bu, projenin geri kalanıyla aynı "minimal bağımlılık"
felsefesini takip eder (bkz. backend/services/ai_client.py).
"""

from __future__ import annotations

from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from backend.database import get_user_by_id

ROLE_RANK = {"free": 0, "pro": 1, "admin": 2}


def load_logged_in_user() -> None:
    """Populate `g.user` from the session at the start of each request.

    Registered as a `before_request` hook in the app factory.
    """
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    user = get_user_by_id(user_id)
    if user is None or not user["is_active"]:
        # Hesap silinmiş/dondurulmuş: oturumu temizle.
        session.clear()
        g.user = None
        return

    g.user = user


def current_user() -> dict | None:
    """Return the logged-in user dict, or None."""
    return getattr(g, "user", None)


def is_pro(user: dict | None = None) -> bool:
    """Return True if the user has pro-level access (pro or admin)."""
    user = user or current_user()
    if not user:
        return False
    return ROLE_RANK.get(user["role"], 0) >= ROLE_RANK["pro"]


def is_admin(user: dict | None = None) -> bool:
    """Return True if the user is an admin."""
    user = user or current_user()
    return bool(user and user["role"] == "admin")


def login_required(view):
    """Redirect anonymous visitors to the login page, keeping their destination."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Bu sayfayı görüntülemek için giriş yapmalısınız.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(min_role: str):
    """Require the current user to have at least `min_role` (free < pro < admin)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                flash("Bu sayfayı görüntülemek için giriş yapmalısınız.", "error")
                return redirect(url_for("auth.login", next=request.path))
            if ROLE_RANK.get(user["role"], 0) < ROLE_RANK.get(min_role, 99):
                flash("Bu özellik için yetkiniz yok.", "error")
                return redirect(url_for("main.index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
