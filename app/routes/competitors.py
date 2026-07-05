"""
Rakip araştırması modülü.

Not: Bu modül Claude'un genel bilgisine dayanarak olası rakipleri ve
konumlandırma önerilerini üretir. Gerçek zamanlı/güncel rakip verisi için
ileride bir web arama servisi (örn. Anthropic web search tool veya SerpAPI)
entegre edilmesi önerilir — bkz. README.
"""

from flask import Blueprint, render_template, request
from app.services.claude_client import ask_claude, safe_parse_json

competitors_bp = Blueprint("competitors", __name__, template_folder="../templates")

SYSTEM_PROMPT = """Sen bir pazar araştırması uzmanısın. Verilen girişim fikri
için olası rakipleri ve konumlandırma önerisini üret. Cevabını SADECE şu JSON
şemasına uygun ver:

{
  "competitors": [
    {"name": "...", "description": "...", "strengths": ["..."], "weaknesses": ["..."]}
  ],
  "positioning_advice": "..."
}

3-5 rakip öner. Türkçe yaz."""


@competitors_bp.route("/", methods=["GET"])
def competitors_form():
    return render_template("competitors.html", result=None)


@competitors_bp.route("/analyze", methods=["POST"])
def analyze_competitors():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()
    region = request.form.get("region", "").strip()

    if not idea:
        return render_template("competitors.html", result=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}\nSektör: {sector or 'belirtilmedi'}\nPazar bölgesi: {region or 'belirtilmedi'}"

    try:
        raw = ask_claude(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1400,
            json_mode=True,
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("competitors.html", result=None, error=f"Analiz sırasında hata oluştu: {exc}")

    return render_template("competitors.html", result=result)
