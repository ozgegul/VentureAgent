"""Gelir modeli önerisi modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import append_analysis, build_enriched_prompt, get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

revenue_bp = Blueprint("revenue", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("revenue")


@revenue_bp.route("/", methods=["GET"])
def revenue_form():
    ctx = get_active_idea()
    return render_template("revenue.html", result=None, active_idea=ctx)


@revenue_bp.route("/analyze", methods=["POST"])
def analyze_revenue():
    idea = request.form.get("idea", "").strip()
    target_audience = request.form.get("target_audience", "").strip()
    pricing_preference = request.form.get("pricing_preference", "").strip()

    if not idea:
        return render_template("revenue.html", result=None, error="Fikir alanı zorunludur.")

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Hedef kitle: {target_audience or 'belirtilmedi'}\n"
        f"Fiyatlandırma tercihi: {pricing_preference or 'belirtilmedi'}"
    )

    try:
        enriched_system = build_enriched_prompt("revenue", SYSTEM_PROMPT)
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=enriched_system,
            max_tokens=2500,
            json_mode=True,
            module="revenue",
            task_complexity="medium",
            response_schema=get_prompt_schema("revenue"),
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("revenue.html", result=None, error=f"Analiz sırasında hata oluştu: {exc}")

    # Phase 3: Store revenue result for downstream modules
    append_analysis("revenue", result)

    return render_template("revenue.html", result=result)
