"""
Fikir analizi modülü.
Diğer modüller (swot, competitors, revenue, roadmap, kanban, investors, pitch)
aynı pattern'i takip ederek genişletilir: bir form sayfası (GET) + Claude'a
istek atan bir sonuç sayfası (POST).
"""

from flask import Blueprint, render_template, request
from backend.auth import current_user, login_required
from backend.database import save_idea_analysis
from backend.services.ai_client import ask_ai
from data_science.pipelines.market_scoring import StartupSignal, build_venture_score

idea_bp = Blueprint("idea", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen deneyimli bir startup mentörüsün. Kullanıcının girişim
fikrini analiz et. Net, yapıcı ve uygulanabilir geri bildirim ver. Türkçe cevap ver."""


@idea_bp.route("/", methods=["GET"])
@login_required
def idea_form():
    """Fikir giriş formunu gösterir."""
    return render_template("idea.html", analysis=None, venture_score=None)


def _form_score(name: str, default: int = 3) -> int:
    """Formdan gelen 1-5 skorunu güvenli şekilde okur."""
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


@idea_bp.route("/analyze", methods=["POST"])
@login_required
def analyze_idea():
    """Formdan gelen fikri Claude'a gönderir ve analiz sonucunu gösterir."""
    user_id = current_user()["id"]
    idea = request.form.get("idea", "").strip()
    problem = request.form.get("problem", "").strip()
    target_audience = request.form.get("target_audience", "").strip()
    sector = request.form.get("sector", "").strip()
    signal = StartupSignal(
        problem_severity=_form_score("problem_severity"),
        target_audience_clarity=_form_score("target_audience_clarity"),
        competition_intensity=_form_score("competition_intensity"),
        monetization_clarity=_form_score("monetization_clarity"),
    )
    venture_score = build_venture_score(signal)

    if not idea or not problem:
        return render_template(
            "idea.html",
            analysis=None,
            venture_score=None,
            error="Fikir ve çözülen problem alanları zorunludur.",
        )

    user_prompt = f"""
Fikir: {idea}
Çözülen problem: {problem}
Hedef kitle: {target_audience or "belirtilmedi"}
Sektör: {sector or "belirtilmedi"}
Data science sinyalleri:
- Problem aciliyeti: {signal.problem_severity}/5
- Hedef kitle netliği: {signal.target_audience_clarity}/5
- Rekabet yoğunluğu: {signal.competition_intensity}/5
- Gelir modeli netliği: {signal.monetization_clarity}/5
- Venture Score: {venture_score.score}/100 ({venture_score.risk_level})

Bu fikri şu başlıklarla değerlendir:
1. Fikrin güçlü yönleri
2. Potansiyel riskler
3. Pazar fırsatı hakkında ilk izlenim
4. Bir sonraki adım önerisi
"""

    try:
        analysis = ask_ai(user_prompt=user_prompt, system_prompt=SYSTEM_PROMPT, max_tokens=1200)
    except Exception as exc:  # noqa: BLE001
        save_idea_analysis(
            user_id=user_id,
            idea=idea,
            problem=problem,
            target_audience=target_audience,
            sector=sector,
            signal=signal,
            venture_score=venture_score,
            ai_analysis=None,
        )
        return render_template("idea.html", analysis=None, venture_score=venture_score, error=str(exc))

    save_idea_analysis(
        user_id=user_id,
        idea=idea,
        problem=problem,
        target_audience=target_audience,
        sector=sector,
        signal=signal,
        venture_score=venture_score,
        ai_analysis=analysis,
    )
    return render_template("idea.html", analysis=analysis, venture_score=venture_score)
