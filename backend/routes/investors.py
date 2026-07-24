"""Yatırımcı bulma tavsiyeleri modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai
from backend.services.context import get_active_idea
from backend.services.prompts import get_prompt

investors_bp = Blueprint("investors", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("investors")


@investors_bp.route("/", methods=["GET"])
def investors_form():
    ctx = get_active_idea()
    return render_template("investors.html", advice=None, active_idea=ctx)


@investors_bp.route("/advise", methods=["POST"])
def advise_investors():
    idea = request.form.get("idea", "").strip()
    stage = request.form.get("stage", "").strip()
    amount = request.form.get("amount", "").strip()
    geography = request.form.get("geography", "").strip()

    if not idea:
        return render_template("investors.html", advice=None, error="Fikir alanı zorunludur.")

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Aşama: {stage or 'belirtilmedi'}\n"
        f"Aranan yatırım tutarı: {amount or 'belirtilmedi'}\n"
        f"Coğrafya: {geography or 'belirtilmedi'}"
    )

    try:
        advice = ask_ai(user_prompt=user_prompt, system_prompt=SYSTEM_PROMPT, max_tokens=2500, module="investors", task_complexity="medium")
    except Exception as exc:  # noqa: BLE001
        return render_template("investors.html", advice=None, error=str(exc))

    return render_template("investors.html", advice=advice)
