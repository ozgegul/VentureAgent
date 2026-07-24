"""MVP roadmap oluşturma modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import append_analysis, build_enriched_prompt, get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

roadmap_bp = Blueprint("roadmap", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("roadmap")


@roadmap_bp.route("/", methods=["GET"])
def roadmap_form():
    ctx = get_active_idea()
    return render_template("roadmap.html", result=None, active_idea=ctx)


@roadmap_bp.route("/generate", methods=["POST"])
def generate_roadmap():
    idea = request.form.get("idea", "").strip()
    tech_capacity = request.form.get("tech_capacity", "").strip()
    budget = request.form.get("budget", "").strip()

    if not idea:
        return render_template("roadmap.html", result=None, error="Fikir alanı zorunludur.")

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Teknik kapasite: {tech_capacity or 'belirtilmedi'}\n"
        f"Bütçe: {budget or 'belirtilmedi'}"
    )

    try:
        enriched_system = build_enriched_prompt("roadmap", SYSTEM_PROMPT)
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=enriched_system,
            max_tokens=1400,
            json_mode=True,
            module="roadmap",
            task_complexity="high",
            response_schema=get_prompt_schema("roadmap"),
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("roadmap.html", result=None, error=f"Oluşturma sırasında hata oluştu: {exc}")

    # Phase 3: Store roadmap result for downstream modules
    append_analysis("roadmap", result)

    return render_template("roadmap.html", result=result)
