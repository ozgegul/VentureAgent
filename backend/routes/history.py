"""Saved analysis history routes. Herkes yalnızca kendi kayıtlarını görür."""

from flask import Blueprint, abort, redirect, render_template, url_for

from backend.auth import current_user, login_required
from backend.database import (
    delete_idea_analysis,
    delete_module_result,
    get_idea_analysis,
    get_module_result,
    list_idea_analyses,
    list_module_results,
)

history_bp = Blueprint("history", __name__, template_folder="../../frontend/templates")

MODULE_LABELS = {
    "swot": "SWOT Analizi",
    "competitors": "Rakip Araştırması",
    "revenue": "Gelir Modeli",
    "roadmap": "MVP Roadmap",
    "kanban": "Kanban",
    "investors": "Yatırımcı Tavsiyesi",
    "pitch_elevator": "Pitch (Asansör Konuşması)",
    "pitch_deck": "Pitch (Deck)",
}


@history_bp.route("/")
@login_required
def history_page():
    """Show the current user's saved idea analyses and other module results."""
    user_id = current_user()["id"]
    analyses = list_idea_analyses(user_id)
    module_results = list_module_results(user_id)
    for result in module_results:
        result["label"] = MODULE_LABELS.get(result["module"], result["module"])
    return render_template("history.html", analyses=analyses, module_results=module_results)


@history_bp.route("/<int:analysis_id>")
@login_required
def history_detail(analysis_id: int):
    """Show all saved fields for one idea analysis."""
    analysis = get_idea_analysis(analysis_id, current_user()["id"])
    if analysis is None:
        abort(404)

    return render_template("history_detail.html", analysis=analysis)


@history_bp.route("/<int:analysis_id>/delete", methods=["POST"])
@login_required
def delete_history_item(analysis_id: int):
    """Delete a saved idea analysis."""
    delete_idea_analysis(analysis_id, current_user()["id"])
    return redirect(url_for("history.history_page"))


@history_bp.route("/module/<int:result_id>")
@login_required
def module_result_detail(result_id: int):
    """Show one saved SWOT/rakip/gelir/roadmap/kanban/yatırımcı/pitch result."""
    result = get_module_result(result_id, current_user()["id"])
    if result is None:
        abort(404)
    result["label"] = MODULE_LABELS.get(result["module"], result["module"])
    return render_template("module_result_detail.html", result=result)


@history_bp.route("/module/<int:result_id>/delete", methods=["POST"])
@login_required
def delete_module_result_item(result_id: int):
    """Delete one saved module result."""
    delete_module_result(result_id, current_user()["id"])
    return redirect(url_for("history.history_page"))
