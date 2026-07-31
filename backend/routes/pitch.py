"""Asansör konuşması ve pitch deck taslağı hazırlama modülü."""

from flask import Blueprint, render_template, request
from backend.auth import current_user, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

pitch_bp = Blueprint("pitch", __name__, template_folder="../../frontend/templates")

ELEVATOR_SYSTEM_PROMPT = get_prompt("pitch_elevator")

DECK_SYSTEM_PROMPT = get_prompt("pitch_deck")


@pitch_bp.route("/", methods=["GET"])
@login_required
def pitch_form():
    return render_template("pitch.html", elevator=None, slides=None, active_idea=get_active_idea())


@pitch_bp.route("/generate", methods=["POST"])
@login_required
def generate_pitch():
    idea = request.form.get("idea", "").strip()
    pitch_type = request.form.get("pitch_type", "elevator")
    traction = request.form.get("traction", "").strip()

    if not idea:
        return render_template("pitch.html", elevator=None, slides=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    try:
        if pitch_type == "deck":
            user_prompt = f"Fikir: {idea}\nMevcut traction/kanıt: {traction or 'henüz yok'}"
            raw = ask_ai(
                user_prompt=user_prompt,
                system_prompt=build_enriched_prompt("pitch", DECK_SYSTEM_PROMPT),
                max_tokens=1600,
                json_mode=True,
            )
            result = safe_parse_json(raw, get_schema("pitch_deck"))
            slides = result.get("slides", [])
            append_analysis("pitch_deck", {"slides": slides})
            save_module_result(
                user_id=current_user()["id"],
                module="pitch_deck",
                idea=idea,
                input_data={"traction": traction},
                result_data={"slides": slides},
            )
            return render_template("pitch.html", elevator=None, slides=slides, active_idea=get_active_idea())
        else:
            user_prompt = f"Fikir: {idea}"
            elevator = ask_ai(
                user_prompt=user_prompt,
                system_prompt=build_enriched_prompt("pitch", ELEVATOR_SYSTEM_PROMPT),
                max_tokens=2000,
            )
            append_analysis("pitch_elevator", {"elevator": elevator})
            save_module_result(
                user_id=current_user()["id"],
                module="pitch_elevator",
                idea=idea,
                input_data=None,
                result_data={"elevator": elevator},
            )
            return render_template("pitch.html", elevator=elevator, slides=None, active_idea=get_active_idea())
    except Exception as exc:  # noqa: BLE001
        return render_template("pitch.html", elevator=None, slides=None, error=str(exc), active_idea=get_active_idea())
