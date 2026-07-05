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
from app.services.claude_client import ask_claude, safe_parse_json

kanban_bp = Blueprint("kanban", __name__, template_folder="../templates")

SYSTEM_PROMPT = """Sen bir ürün yöneticisisin. Verilen girişim fikri için MVP'yi
hayata geçirmek üzere yapılacak somut görevleri Kanban kartları olarak üret.
Cevabını SADECE şu JSON şemasına uygun ver:

{
  "cards": [
    {"title": "...", "description": "..."}
  ]
}

8-12 kart üret, her biri tek bir somut aksiyon içersin (örn. "Landing page
tasarımını oluştur", "İlk 10 kullanıcı görüşmesini yap"). Türkçe yaz."""


@kanban_bp.route("/", methods=["GET"])
def kanban_form():
    return render_template("kanban.html", cards=None)


@kanban_bp.route("/generate", methods=["POST"])
def generate_kanban():
    idea = request.form.get("idea", "").strip()

    if not idea:
        return render_template("kanban.html", cards=None, error="Fikir alanı zorunludur.")

    user_prompt = f"Fikir: {idea}"

    try:
        raw = ask_claude(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1200,
            json_mode=True,
        )
        result = safe_parse_json(raw)
        cards = result.get("cards", [])
    except Exception as exc:  # noqa: BLE001
        return render_template("kanban.html", cards=None, error=f"Oluşturma sırasında hata oluştu: {exc}")

    return render_template("kanban.html", cards=cards)
