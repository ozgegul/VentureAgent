"""
Kanban board modülü.

Akış: Kullanıcı fikrini girer → Claude, MVP için başlangıç görev kartları
üretir (JSON) → Kartlar "Yapılacak" sütununda gösterilir → Kullanıcı
sürükle-bırak ile kartları sütunlar arasında taşıyabilir (kanban.js).

Not: Bu sürümde board durumu tarayıcıda (client-side) tutulur, sayfa
yenilendiğinde sıfırlanır. Kalıcı depolama istenirse bir veritabanı
(örn. SQLite) eklenip kartlar kullanıcıya/projeye bağlı olarak saklanabilir.
"""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.context import get_active_idea
from backend.services.prompts import get_prompt, get_prompt_schema

kanban_bp = Blueprint("kanban", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("kanban")


@kanban_bp.route("/", methods=["GET"])
def kanban_form():
    ctx = get_active_idea()
    return render_template("kanban.html", cards=None, active_idea=ctx)


@kanban_bp.route("/generate", methods=["POST"])
def generate_kanban():
    idea = request.form.get("idea", "").strip()

    if not idea:
        return render_template("kanban.html", cards=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}"

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=2500,
            json_mode=True,
            module="kanban",
            task_complexity="medium",
            response_schema=get_prompt_schema("kanban"),
        )
        result = safe_parse_json(raw)
        cards = result.get("cards", [])
    except Exception as exc:  # noqa: BLE001
        return render_template("kanban.html", cards=None, error=f"Oluşturma sırasında hata oluştu: {exc}")

    return render_template("kanban.html", cards=cards)
