"""Saved analysis history routes."""

from flask import Blueprint, abort, redirect, render_template, url_for

from backend.database import (
    delete_idea_analysis,
    get_idea_analysis,
    list_idea_analyses,
)
from backend.routes.admin import admin_required

history_bp = Blueprint("history", __name__, template_folder="../../frontend/templates")


@history_bp.route("/")
@admin_required
def history_page():
    """Show latest saved idea analyses."""
    analyses = list_idea_analyses()
    return render_template("history.html", analyses=analyses)


@history_bp.route("/<int:analysis_id>")
@admin_required
def history_detail(analysis_id: int):
    """Show all saved fields for one idea analysis."""
    analysis = get_idea_analysis(analysis_id)
    if analysis is None:
        abort(404)

    return render_template("history_detail.html", analysis=analysis)


@history_bp.route("/<int:analysis_id>/delete", methods=["POST"])
@admin_required
def delete_history_item(analysis_id: int):
    """Delete a saved idea analysis."""
    delete_idea_analysis(analysis_id)
    return redirect(url_for("history.history_page"))
