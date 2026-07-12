"""Saved analysis history routes."""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from backend.database import (
    delete_idea_analysis,
    get_idea_analysis,
    list_idea_analyses,
    save_mentor_evaluation,
)

history_bp = Blueprint("history", __name__, template_folder="../../frontend/templates")


@history_bp.route("/")
def history_page():
    """Show latest saved idea analyses."""
    analyses = list_idea_analyses()
    return render_template("history.html", analyses=analyses)


@history_bp.route("/<int:analysis_id>")
def history_detail(analysis_id: int):
    """Show all saved fields for one idea analysis."""
    analysis = get_idea_analysis(analysis_id)
    if analysis is None:
        abort(404)

    return render_template("history_detail.html", analysis=analysis)


@history_bp.route("/<int:analysis_id>/delete", methods=["POST"])
def delete_history_item(analysis_id: int):
    """Delete a saved idea analysis."""
    delete_idea_analysis(analysis_id)
    return redirect(url_for("history.history_page"))


@history_bp.route("/<int:analysis_id>/mentor", methods=["POST"])
def save_mentor_labels(analysis_id: int):
    """Save mentor labels for a saved idea analysis."""
    if get_idea_analysis(analysis_id) is None:
        abort(404)

    save_mentor_evaluation(
        analysis_id=analysis_id,
        problem_clarity=_form_score("mentor_problem_clarity"),
        market_potential=_form_score("mentor_market_potential"),
        revenue_potential=_form_score("mentor_revenue_potential"),
        mvp_feasibility=_form_score("mentor_mvp_feasibility"),
        overall_score=_form_score("mentor_overall_score"),
        notes=request.form.get("mentor_notes", ""),
    )
    return redirect(url_for("history.history_detail", analysis_id=analysis_id))


def _form_score(name: str) -> int:
    """Read a 1-5 score from form data."""
    try:
        return max(1, min(5, int(request.form.get(name, 3))))
    except (TypeError, ValueError):
        return 3
