"""MVP roadmap oluşturma modülü."""

from flask import Blueprint, render_template, request
from backend.auth import current_user, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

roadmap_bp = Blueprint("roadmap", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("roadmap")


@roadmap_bp.route("/", methods=["GET"])
@login_required
def roadmap_form():
    return render_template("roadmap.html", result=None, active_idea=get_active_idea())


@roadmap_bp.route("/generate", methods=["POST"])
@login_required
def generate_roadmap():
    idea = request.form.get("idea", "").strip()
    tech_capacity = request.form.get("tech_capacity", "").strip()
    budget = request.form.get("budget", "").strip()

    if not idea:
        return render_template("roadmap.html", result=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Teknik kapasite: {tech_capacity or 'belirtilmedi'}\n"
        f"Bütçe: {budget or 'belirtilmedi'}"
    )

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=build_enriched_prompt("roadmap", SYSTEM_PROMPT),
            max_tokens=1400,
            json_mode=True,
            module="roadmap",
            task_complexity="high",
            response_schema=get_schema("roadmap"),
        )
        result = safe_parse_json(raw, get_schema("roadmap"))
    except Exception as exc:  # noqa: BLE001
        return render_template("roadmap.html", result=None, error=f"Oluşturma sırasında hata oluştu: {exc}", active_idea=get_active_idea())

    append_analysis("roadmap", locals().get("roadmap") or locals().get("result") or locals().get("kanban"))
    save_module_result(
        user_id=current_user()["id"],
        module="roadmap",
        idea=idea,
        input_data={"tech_capacity": tech_capacity, "budget": budget},
        result_data=result,
    )
    return render_template("roadmap.html", result=result, active_idea=get_active_idea())
