"""Public user-owned analysis history routes."""

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from backend.database import (
    get_public_idea_analysis,
    hide_public_idea_analysis,
    list_session_idea_analyses,
    save_mentor_evaluation,
)

public_history_bp = Blueprint(
    "public_history",
    __name__,
    template_folder="../../frontend/templates",
)


@public_history_bp.route("/")
def public_history_page():
    """Show analyses created in the current browser session."""
    session_id = session.get("visitor_id")
    analyses = list_session_idea_analyses(session_id) if session_id else []
    return render_template("public_history.html", analyses=analyses)


@public_history_bp.route("/latest")
def public_history_latest():
    """Redirect to the latest analysis for this browser session."""
    session_id = session.get("visitor_id")
    analyses = list_session_idea_analyses(session_id, limit=1) if session_id else []
    if not analyses:
        return redirect(url_for("public_history.public_history_page"))

    return redirect(
        url_for(
            "public_history.public_history_detail",
            token=analyses[0]["public_token"],
        )
    )


@public_history_bp.route("/<token>")
def public_history_detail(token: str):
    """Show one analysis only when it belongs to this browser session."""
    session_id = session.get("visitor_id")
    if not session_id:
        abort(404)

    analysis = get_public_idea_analysis(token, session_id)
    if analysis is None:
        abort(404)

    return render_template("public_history_detail.html", analysis=analysis)


@public_history_bp.route("/<token>/delete", methods=["POST"])
def public_history_delete(token: str):
    """Delete one analysis only when it belongs to this browser session."""
    session_id = session.get("visitor_id")
    if not session_id:
        abort(404)

    analysis = get_public_idea_analysis(token, session_id)
    if analysis is None:
        abort(404)

    hide_public_idea_analysis(analysis["id"])
    return redirect(url_for("public_history.public_history_page"))


@public_history_bp.route("/<token>/feedback", methods=["POST"])
def public_history_feedback(token: str):
    """Save user feedback labels for one owned analysis."""
    session_id = session.get("visitor_id")
    if not session_id:
        abort(404)

    analysis = get_public_idea_analysis(token, session_id)
    if analysis is None:
        abort(404)

    save_mentor_evaluation(
        analysis_id=analysis["id"],
        problem_clarity=_form_score("mentor_problem_clarity"),
        market_potential=_form_score("mentor_market_potential"),
        revenue_potential=_form_score("mentor_revenue_potential"),
        mvp_feasibility=_form_score("mentor_mvp_feasibility"),
        overall_score=_form_score("mentor_overall_score"),
        notes=request.form.get("mentor_notes", ""),
    )
    return redirect(url_for("public_history.public_history_detail", token=token))


def _form_score(name: str) -> int:
    """Read a 1-5 score from form data."""
    try:
        return max(1, min(5, int(request.form.get(name, 3))))
    except (TypeError, ValueError):
        return 3
