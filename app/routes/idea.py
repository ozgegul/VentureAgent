"""
Fikir analizi modülü.
Diğer modüller (swot, competitors, revenue, roadmap, kanban, investors, pitch)
aynı pattern'i takip ederek genişletilir: bir form sayfası (GET) + Claude'a
istek atan bir sonuç sayfası (POST).
"""

from flask import Blueprint, render_template, request
from app.services.claude_client import ask_claude

idea_bp = Blueprint("idea", __name__, template_folder="../templates")

SYSTEM_PROMPT = """Sen deneyimli bir startup mentörüsün. Kullanıcının girişim
fikrini analiz et. Net, yapıcı ve uygulanabilir geri bildirim ver. Türkçe cevap ver."""


@idea_bp.route("/", methods=["GET"])
def idea_form():
    """Fikir giriş formunu gösterir."""
    return render_template("idea.html", analysis=None)


@idea_bp.route("/analyze", methods=["POST"])
def analyze_idea():
    """Formdan gelen fikri Claude'a gönderir ve analiz sonucunu gösterir."""
    idea = request.form.get("idea", "").strip()
    problem = request.form.get("problem", "").strip()
    target_audience = request.form.get("target_audience", "").strip()
    sector = request.form.get("sector", "").strip()

    if not idea or not problem:
        return render_template(
            "idea.html",
            analysis=None,
            error="Fikir ve çözülen problem alanları zorunludur.",
        )

    user_prompt = f"""
Fikir: {idea}
Çözülen problem: {problem}
Hedef kitle: {target_audience or "belirtilmedi"}
Sektör: {sector or "belirtilmedi"}

Bu fikri şu başlıklarla değerlendir:
1. Fikrin güçlü yönleri
2. Potansiyel riskler
3. Pazar fırsatı hakkında ilk izlenim
4. Bir sonraki adım önerisi
"""

    try:
        analysis = ask_claude(user_prompt=user_prompt, system_prompt=SYSTEM_PROMPT, max_tokens=1200)
    except Exception as exc:  # noqa: BLE001
        return render_template("idea.html", analysis=None, error=str(exc))

    return render_template("idea.html", analysis=analysis)
