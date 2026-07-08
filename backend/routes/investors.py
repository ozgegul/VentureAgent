"""Yatırımcı bulma tavsiyeleri modülü."""

from flask import Blueprint, render_template, request
from backend.services.ai_client import ask_ai

investors_bp = Blueprint("investors", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen bir girişim sermayesi (VC) danışmanısın. Kullanıcının
girişimi için yatırımcı bulma stratejisi öner. Şu başlıklarda yaz:
1. Hangi tür yatırımcı aranmalı (melek yatırımcı, VC, hızlandırıcı vb.)
2. Bu aşamada hangi platformlar/topluluklar araştırılmalı
3. Yatırımcıya ulaşmadan önce hazırlanması gerekenler
4. İlk teması nasıl kurmalı (soğuk e-posta, tanıdık üzerinden vb.)
Türkçe, net ve uygulanabilir yaz."""


@investors_bp.route("/", methods=["GET"])
def investors_form():
    return render_template("investors.html", advice=None)


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
        advice = ask_ai(user_prompt=user_prompt, system_prompt=SYSTEM_PROMPT, max_tokens=1200)
    except Exception as exc:  # noqa: BLE001
        return render_template("investors.html", advice=None, error=str(exc))

    return render_template("investors.html", advice=advice)
