"""Data science dashboard routes."""

from flask import Blueprint, render_template

from backend.database import get_dashboard_metrics
from backend.routes.admin import admin_required

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../frontend/templates")


@dashboard_bp.route("/")
@admin_required
def dashboard_page():
    """Show aggregate VentureAgent data science metrics."""
    metrics = get_dashboard_metrics()
    return render_template("dashboard.html", metrics=metrics)
