"""Gelir modeli önerisi modülü."""

from flask import Blueprint, render_template, request
from app.services.claude_client import ask_claude, safe_parse_json

revenue_bp = Blueprint("revenue", __name__, template_folder="../templates")

SYSTEM_PROMPT = """Sen bir iş modeli danışmanısın. Verilen girişim fikri için
uygun gelir modellerini öner. Cevabını SADECE şu JSON şemasına uygun ver:

{
  "models": [
    {"name": "...", "description": "...", "pros": ["..."], "cons": ["..."]}
  ],
  "recommended": "..."
}

2-4 gelir modeli öner (örn. abonelik, komisyon, freemium, tek seferlik satış,
reklam). "recommended" alanında hangisini neden önerdiğini kısaca açıkla.
Türkçe yaz."""


@revenue_bp.route("/", methods=["GET"])
def revenue_form():
    return render_template("revenue.html", result=None)


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
        raw = ask_claude(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1200,
            json_mode=True,
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("revenue.html", result=None, error=f"Analiz sırasında hata oluştu: {exc}")

    return render_template("revenue.html", result=result)
