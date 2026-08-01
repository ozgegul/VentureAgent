"""
SWOT analizi modülü.
Claude'dan yapılandırılmış JSON istenir (json_mode=True) ve 2x2 grid olarak gösterilir.
"""

from flask import Blueprint, abort, render_template, request, Response
from backend.auth import current_user, login_required
from backend.database import get_module_result, save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.pdf_export import build_swot_pdf
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

swot_bp = Blueprint("swot", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("swot")


@swot_bp.route("/", methods=["GET"])
@login_required
def swot_form():
    return render_template("swot.html", swot=None, active_idea=get_active_idea())


@swot_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_swot():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()

    if not idea:
        return render_template("swot.html", swot=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    user_prompt = f"Fikir: {idea}\nSektör: {sector or 'belirtilmedi'}"

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=build_enriched_prompt("swot", SYSTEM_PROMPT),
            max_tokens=1000,
            json_mode=True,
            module="swot",
            task_complexity="high",
            response_schema=get_schema("swot"),
        )
        swot = safe_parse_json(raw, get_schema("swot"))
    except Exception as exc:  # noqa: BLE001
        return render_template("swot.html", swot=None, error=f"Analiz sırasında hata oluştu: {exc}", active_idea=get_active_idea())

    append_analysis("swot", locals().get("swot") or locals().get("result") or locals().get("kanban"))
    result_id = save_module_result(
        user_id=current_user()["id"],
        module="swot",
        idea=idea,
        input_data={"sector": sector},
        result_data=swot,
    )
    return render_template("swot.html", swot=swot, result_id=result_id, active_idea=get_active_idea())


@swot_bp.route("/pdf/<int:result_id>")
@login_required
def download_swot_pdf(result_id: int):
    """Return a saved SWOT result as a downloadable PDF."""
    result = get_module_result(result_id, current_user()["id"])
    if result is None or result["module"] != "swot":
        abort(404)

    pdf_bytes = build_swot_pdf(
        idea=result["idea"],
        sector=(result["input_data"] or {}).get("sector"),
        swot=result["result_data"],
    )
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="swot-analizi-{result_id}.pdf"'},
    )
