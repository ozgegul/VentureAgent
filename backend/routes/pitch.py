"""Asansör konuşması ve pitch deck taslağı hazırlama modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import append_analysis, build_enriched_prompt, get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

pitch_bp = Blueprint("pitch", __name__, template_folder="../../frontend/templates")

ELEVATOR_SYSTEM_PROMPT = get_prompt("pitch_elevator")

DECK_SYSTEM_PROMPT = get_prompt("pitch_deck")


@pitch_bp.route("/", methods=["GET"])
def pitch_form():
    ctx = get_active_idea()
    return render_template("pitch.html", elevator=None, slides=None, active_idea=ctx)


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
            enriched_system = build_enriched_prompt("pitch", DECK_SYSTEM_PROMPT)
            raw = ask_ai(
                user_prompt=user_prompt,
                system_prompt=enriched_system,
                max_tokens=1600,
                json_mode=True,
                module="pitch",
                task_complexity="high",
                response_schema=get_prompt_schema("pitch_deck"),
            )
            result = safe_parse_json(raw)

            # Phase 3: Store pitch deck result for downstream modules
            append_analysis("pitch_deck", result)

            return render_template("pitch.html", elevator=None, slides=result.get("slides", []))
        else:
            user_prompt = f"Fikir: {idea}"
            enriched_system = build_enriched_prompt("pitch", ELEVATOR_SYSTEM_PROMPT)
            elevator = ask_ai(
                user_prompt=user_prompt,
                system_prompt=enriched_system,
                max_tokens=400,
                module="pitch",
                task_complexity="low",
            )

            # Phase 3: Store elevator pitch result for downstream modules
            append_analysis("pitch_elevator", elevator)

            return render_template("pitch.html", elevator=elevator, slides=None)
    except Exception as exc:  # noqa: BLE001
        return render_template("pitch.html", elevator=None, slides=None, error=str(exc))
