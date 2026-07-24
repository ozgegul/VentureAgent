"""Asansör konuşması ve pitch deck taslağı hazırlama modülü."""

from flask import Blueprint, render_template, request
from backend.auth import current_user, is_pro, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.file_helper import build_attachment_prompt

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
@login_required
def pitch_form():
    return render_template("pitch.html", elevator=None, slides=None)


@pitch_bp.route("/generate", methods=["POST"])
@login_required
def generate_pitch():
    idea = request.form.get("idea", "").strip()
    pitch_type = request.form.get("pitch_type", "elevator")
    traction = request.form.get("traction", "").strip()
    attachment = request.files.get("attachment")
    if attachment and not is_pro():
        return render_template("pitch.html", elevator=None, slides=None, error="Dosya yükleme yalnızca Pro/Admin kullanıcılar için kullanılabilir.")
    attachment_prompt, attachment_info = build_attachment_prompt(attachment)
    attachment_name = attachment_info["display_name"] if attachment_info else None

    if not idea:
        return render_template("pitch.html", elevator=None, slides=None, error="Fikir alanı zorunludur.", attachment_name=attachment_name)

    try:
        if pitch_type == "deck":
            user_prompt = f"Fikir: {idea}\nMevcut traction/kanıt: {traction or 'henüz yok'}{attachment_prompt}"
            raw = ask_ai(
                user_prompt=user_prompt,
                system_prompt=DECK_SYSTEM_PROMPT,
                max_tokens=1600,
                json_mode=True,
            )
            result = safe_parse_json(raw)
            slides = result.get("slides", [])
            save_module_result(
                user_id=current_user()["id"],
                module="pitch_deck",
                idea=idea,
                input_data={"traction": traction, "attachment": attachment_info["meta"] if attachment_info else None},
                result_data={"slides": slides},
            )
            return render_template("pitch.html", elevator=None, slides=slides)
        else:
            user_prompt = f"Fikir: {idea}{attachment_prompt}"
            elevator = ask_ai(
                user_prompt=user_prompt,
                system_prompt=ELEVATOR_SYSTEM_PROMPT,
                max_tokens=400,
            )
            save_module_result(
                user_id=current_user()["id"],
                module="pitch_elevator",
                idea=idea,
                input_data={"attachment": attachment_info["meta"] if attachment_info else None},
                result_data={"elevator": elevator},
            )
            return render_template("pitch.html", elevator=elevator, slides=None)
    except Exception as exc:  # noqa: BLE001
        return render_template("pitch.html", elevator=None, slides=None, error=str(exc))
