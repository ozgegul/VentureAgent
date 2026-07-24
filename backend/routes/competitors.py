"""
Rakip araştırması modülü.

Not: Bu modül Claude'un genel bilgisine dayanarak olası rakipleri ve
konumlandırma önerilerini üretir. Gerçek zamanlı/güncel rakip verisi için
ileride bir web arama servisi (örn. Anthropic web search tool veya SerpAPI)
entegre edilmesi önerilir — bkz. README.
"""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import append_analysis, build_enriched_prompt, get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

competitors_bp = Blueprint("competitors", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("competitors")


@competitors_bp.route("/", methods=["GET"])
def competitors_form():
    ctx = get_active_idea()
    return render_template("competitors.html", result=None, active_idea=ctx)


@competitors_bp.route("/analyze", methods=["POST"])
def analyze_competitors():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()
    region = request.form.get("region", "").strip()

    if not idea:
        return render_template("competitors.html", result=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}\nSektör: {sector or 'belirtilmedi'}\nPazar bölgesi: {region or 'belirtilmedi'}"

    try:
        enriched_system = build_enriched_prompt("competitors", SYSTEM_PROMPT)
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=enriched_system,
            max_tokens=1400,
            json_mode=True,
            module="competitors",
            task_complexity="medium",
            response_schema=get_prompt_schema("competitors"),
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("competitors.html", result=None, error=f"Analiz sırasında hata oluştu: {exc}")

    # Phase 3: Store competitors result for downstream modules
    append_analysis("competitors", result)

    return render_template("competitors.html", result=result)
