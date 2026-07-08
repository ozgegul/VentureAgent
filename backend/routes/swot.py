"""
SWOT analizi modülü.
Claude'dan yapılandırılmış JSON istenir (json_mode=True) ve 2x2 grid olarak gösterilir.
"""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json

swot_bp = Blueprint("swot", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen deneyimli bir startup stratejistisin. Verilen girişim
fikri için SWOT analizi yap. Cevabını SADECE şu JSON şemasına uygun ver:

{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "opportunities": ["...", "..."],
  "threats": ["...", "..."]
}

Her liste 3-5 madde içersin, maddeler kısa ve net olsun. Türkçe yaz."""


@swot_bp.route("/", methods=["GET"])
def swot_form():
    return render_template("swot.html", swot=None)


@swot_bp.route("/analyze", methods=["POST"])
def analyze_swot():
    idea = request.form.get("idea", "").strip()
    sector = request.form.get("sector", "").strip()

    if not idea:
        return render_template("swot.html", swot=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}\nSektör: {sector or 'belirtilmedi'}"

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1000,
            json_mode=True,
        )
        swot = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("swot.html", swot=None, error=f"Analiz sırasında hata oluştu: {exc}")

    return render_template("swot.html", swot=swot)
