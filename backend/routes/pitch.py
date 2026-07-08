"""Asansör konuşması ve pitch deck taslağı hazırlama modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json

pitch_bp = Blueprint("pitch", __name__, template_folder="../../frontend/templates")

ELEVATOR_SYSTEM_PROMPT = """Sen bir pitch koçusun. Verilen girişim fikri için
30 saniyelik, akıcı ve ikna edici bir asansör konuşması (elevator pitch) yaz.
Türkçe yaz, tek paragraf olsun, abartılı pazarlama dilinden kaçın."""

DECK_SYSTEM_PROMPT = """Sen bir pitch deck danışmanısın. Verilen girişim fikri
için yatırımcı sunumu slayt taslağı oluştur. Cevabını SADECE şu JSON şemasına
uygun ver:

{
  "slides": [
    {"title": "...", "content": "..."}
  ]
}

Şu sırayla 8-10 slayt üret: Problem, Çözüm, Pazar Büyüklüğü, Ürün, İş Modeli,
Traction/Kanıt, Rekabet, Ekip, Finansal Projeksiyon, Yatırım Talebi. Her
slaytın "content" alanı 2-3 madde halinde kısa olsun. Türkçe yaz."""


@pitch_bp.route("/", methods=["GET"])
def pitch_form():
    return render_template("pitch.html", elevator=None, slides=None)


@pitch_bp.route("/generate", methods=["POST"])
def generate_pitch():
    idea = request.form.get("idea", "").strip()
    pitch_type = request.form.get("pitch_type", "elevator")
    traction = request.form.get("traction", "").strip()

    if not idea:
        return render_template("pitch.html", elevator=None, slides=None, error="Fikir alanı zorunludur.")

    try:
        if pitch_type == "deck":
            user_prompt = f"Fikir: {idea}\nMevcut traction/kanıt: {traction or 'henüz yok'}"
            raw = ask_ai(
                user_prompt=user_prompt,
                system_prompt=DECK_SYSTEM_PROMPT,
                max_tokens=1600,
                json_mode=True,
            )
            result = safe_parse_json(raw)
            return render_template("pitch.html", elevator=None, slides=result.get("slides", []))
        else:
            user_prompt = f"Fikir: {idea}"
            elevator = ask_ai(
                user_prompt=user_prompt,
                system_prompt=ELEVATOR_SYSTEM_PROMPT,
                max_tokens=400,
            )
            return render_template("pitch.html", elevator=elevator, slides=None)
    except Exception as exc:  # noqa: BLE001
        return render_template("pitch.html", elevator=None, slides=None, error=str(exc))
