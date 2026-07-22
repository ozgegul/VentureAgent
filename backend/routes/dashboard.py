"""Data science dashboard routes (kullanıcıya özel metrikler)."""

from flask import Blueprint, render_template

from backend.auth import current_user, login_required
from backend.database import get_dashboard_metrics

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../frontend/templates")


@dashboard_bp.route("/")
@login_required
def dashboard_page():
    """Show the current user's aggregate VentureAgent metrics."""
    metrics = get_dashboard_metrics(current_user()["id"])
    return render_template("dashboard.html", metrics=metrics)
