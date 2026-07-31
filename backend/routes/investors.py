"""Yatırımcı bulma tavsiyeleri modülü."""

from flask import Blueprint, render_template, request
from backend.auth import current_user, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

investors_bp = Blueprint("investors", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("investors")


@investors_bp.route("/", methods=["GET"])
@login_required
def investors_form():
    return render_template("investors.html", advice=None, active_idea=get_active_idea())


@investors_bp.route("/advise", methods=["POST"])
@login_required
def advise_investors():
    idea = request.form.get("idea", "").strip()
    stage = request.form.get("stage", "").strip()
    amount = request.form.get("amount", "").strip()
    geography = request.form.get("geography", "").strip()

    if not idea:
        return render_template("investors.html", advice=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    user_prompt = (
        f"Fikir: {idea}\n"
        f"Aşama: {stage or 'belirtilmedi'}\n"
        f"Aranan yatırım tutarı: {amount or 'belirtilmedi'}\n"
        f"Coğrafya: {geography or 'belirtilmedi'}"
    )

    try:
        advice = ask_ai(
            user_prompt=user_prompt,
            system_prompt=build_enriched_prompt("investors", SYSTEM_PROMPT),
            max_tokens=4000,
            module="investors",
            task_complexity="medium",
        )
    except Exception as exc:  # noqa: BLE001
        return render_template("investors.html", advice=None, error=str(exc), active_idea=get_active_idea())

    append_analysis("investors", {"advice": advice})
    save_module_result(
        user_id=current_user()["id"],
        module="investors",
        idea=idea,
        input_data={"stage": stage, "amount": amount, "geography": geography},
        result_data={"advice": advice},
    )
    return render_template("investors.html", advice=advice, active_idea=get_active_idea())
