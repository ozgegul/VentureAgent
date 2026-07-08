"""MVP roadmap oluşturma modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json

roadmap_bp = Blueprint("roadmap", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen bir ürün yöneticisisin. Verilen girişim fikri için MVP'ye
giden bir yol haritası (roadmap) oluştur. Cevabını SADECE şu JSON şemasına
uygun ver:

{
  "items": [
    {"phase": "mvp", "title": "...", "description": "...", "estimated_weeks": 2}
  ]
}

"phase" değeri şunlardan biri olmalı: "mvp", "beta", "launch", "growth".
Toplam 6-10 madde üret, mantıklı sırada. Türkçe yaz."""


@roadmap_bp.route("/", methods=["GET"])
def roadmap_form():
    return render_template("roadmap.html", result=None)


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
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1400,
            json_mode=True,
        )
        result = safe_parse_json(raw)
    except Exception as exc:  # noqa: BLE001
        return render_template("roadmap.html", result=None, error=f"Oluşturma sırasında hata oluştu: {exc}")

    return render_template("roadmap.html", result=result)
