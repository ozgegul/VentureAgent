"""Data science dashboard routes."""

from flask import Blueprint, render_template

from backend.database import get_dashboard_metrics

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../frontend/templates")


@dashboard_bp.route("/")
def dashboard_page():
    """Show aggregate VentureAgent data science metrics."""
    metrics = get_dashboard_metrics()
    return render_template("dashboard.html", metrics=metrics)
