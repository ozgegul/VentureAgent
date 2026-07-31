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
from backend.auth import current_user, login_required
from backend.database import save_module_result
from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.prompts import get_prompt, get_schema
from backend.services.context import get_active_idea, append_analysis, build_enriched_prompt

kanban_bp = Blueprint("kanban", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("kanban")


@kanban_bp.route("/", methods=["GET"])
@login_required
def kanban_form():
    return render_template("kanban.html", cards=None, active_idea=get_active_idea())


@kanban_bp.route("/generate", methods=["POST"])
@login_required
def generate_kanban():
    idea = request.form.get("idea", "").strip()

    if not idea:
        return render_template("kanban.html", cards=None, error="Fikir alanı zorunludur.", active_idea=get_active_idea())

    user_prompt = f"Fikir: {idea}"

    try:
        raw = ask_ai(
            user_prompt=user_prompt,
            system_prompt=build_enriched_prompt("kanban", SYSTEM_PROMPT),
            max_tokens=1200,
            json_mode=True,
            module="kanban",
            task_complexity="medium",
            response_schema=get_schema("kanban"),
        )
        result = safe_parse_json(raw, get_schema("kanban"))
        cards = result.get("cards", [])
    except Exception as exc:  # noqa: BLE001
        return render_template("kanban.html", cards=None, error=f"Oluşturma sırasında hata oluştu: {exc}", active_idea=get_active_idea())

    append_analysis("kanban", locals().get("kanban") or locals().get("result") or locals().get("kanban"))
    save_module_result(
        user_id=current_user()["id"],
        module="kanban",
        idea=idea,
        input_data=None,
        result_data={"cards": cards},
    )
    return render_template(
        "kanban.html",
        cards=cards,
        note="Kartlar oluşturuldu ve geçmişine kaydedildi. Sürükle-bırak konumları şu an için "
        "yalnızca bu oturumda tarayıcıda tutulur; sayfa yenilenirse konumlar sıfırlanır "
        "(kalıcı konum takibi ayrı bir geliştirme olarak planlanabilir).",
    )
