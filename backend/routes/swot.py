"""
SWOT analizi modülü.
Claude'dan yapılandırılmış JSON istenir (json_mode=True) ve 2x2 grid olarak gösterilir.
"""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import append_analysis, build_enriched_prompt, get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

swot_bp = Blueprint("swot", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("swot")


@swot_bp.route("/", methods=["GET"])
def swot_form():
    ctx = get_active_idea()
    return render_template("swot.html", swot=None, active_idea=ctx)


@swot_bp.route("/analyze", methods=["POST"])
def analyze_swot():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()

    if not idea:
        return render_template("swot.html", swot=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}\nSektör: {sector or 'belirtilmedi'}"

    try:
        enriched_system = build_enriched_prompt("swot", SYSTEM_PROMPT)
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=enriched_system,
            max_tokens=2500,
            json_mode=True,
            module="swot",
            task_complexity="medium",
            response_schema=get_prompt_schema("swot"),
        )
        swot = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("swot.html", swot=None, error=f"Analiz sırasında hata oluştu: {exc}")

    # Phase 3: Store SWOT result for downstream modules
    append_analysis("swot", swot)

    return render_template("swot.html", swot=swot)
