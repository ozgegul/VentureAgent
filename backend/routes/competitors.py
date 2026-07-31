"""
Rakip araştırması modülü.

Not: Bu modül Claude'un genel bilgisine dayanarak olası rakipleri ve
konumlandırma önerilerini üretir. Gerçek zamanlı/güncel rakip verisi için
ileride bir web arama servisi (örn. Anthropic web search tool veya SerpAPI)
entegre edilmesi önerilir — bkz. README.
"""

from flask import Blueprint, render_template, request
from backend.auth import current_user, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

competitors_bp = Blueprint("competitors", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("competitors")


@competitors_bp.route("/", methods=["GET"])
@login_required
def competitors_form():
    return render_template("competitors.html", result=None, active_idea=get_active_idea())


@competitors_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_competitors():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()
    region = request.form.get("region", "").strip()

    if not idea:
        return render_template("competitors.html", result=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Sektör: {sector or 'belirtilmedi'}\n"
        f"Pazar bölgesi: {region or 'belirtilmedi'}"
    )

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=build_enriched_prompt("competitors", SYSTEM_PROMPT),
            max_tokens=1400,
            json_mode=True,
            module="competitors",
            task_complexity="medium",
            response_schema=get_schema("competitors"),
        )
        result = safe_parse_json(raw, get_schema("competitors"))
    except Exception as exc:  # noqa: BLE001
        return render_template("competitors.html", result=None, error=f"Analiz sırasında hata oluştu: {exc}", active_idea=get_active_idea())

    append_analysis("competitors", locals().get("competitors") or locals().get("result") or locals().get("kanban"))
    save_module_result(
        user_id=current_user()["id"],
        module="competitors",
        idea=idea,
        input_data={"sector": sector, "region": region},
        result_data=result,
    )
    return render_template("competitors.html", result=result, active_idea=get_active_idea())
