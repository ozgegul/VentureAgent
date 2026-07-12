"""Guided chat-first idea analysis flow."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, url_for

from backend.database import save_idea_analysis
from backend.services.ai_client import ask_ai
from data_science.pipelines.market_scoring import StartupSignal, build_venture_score

guided_bp = Blueprint("guided", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen VentureAgent'sın. Kullanıcının verdiği kısa cevaplardan
girişim fikrini sade, anlaşılır ve yönlendirici şekilde analiz et. Teknik
terim kullanırsan hemen yanında basit açıklamasını ver. Türkçe cevap ver."""


@guided_bp.route("/", methods=["GET"])
def guided_page():
    """Render the guided chat-first flow."""
    return render_template("guided.html")


@guided_bp.route("/analyze", methods=["POST"])
def analyze_guided():
    """Analyze guided answers, save them, and return a compact result."""
    data = request.get_json(silent=True) or {}

    idea = _text(data.get("idea"))
    problem = _text(data.get("problem"))
    target_audience = _text(data.get("target_audience"))
    sector = _text(data.get("sector"))

    if not idea or not problem:
        return jsonify({"error": "Fikir ve problem cevapları zorunludur."}), 400

    signal = StartupSignal(
        problem_severity=_score(data.get("problem_severity")),
        target_audience_clarity=_score(data.get("target_audience_clarity")),
        competition_intensity=_score(data.get("competition_intensity")),
        monetization_clarity=_score(data.get("monetization_clarity")),
    )
    venture_score = build_venture_score(signal)

    ai_analysis = None
    ai_error = None
    try:
        ai_analysis = ask_ai(
            user_prompt=_build_prompt(
                idea=idea,
                problem=problem,
                target_audience=target_audience,
                sector=sector,
                signal=signal,
                venture_score=venture_score,
            ),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=900,
        )
    except Exception as exc:  # noqa: BLE001
        ai_error = str(exc)

    analysis_id = save_idea_analysis(
        idea=idea,
        problem=problem,
        target_audience=target_audience,
        sector=sector,
        signal=signal,
        venture_score=venture_score,
        ai_analysis=ai_analysis,
    )

    return jsonify(
        {
            "id": analysis_id,
            "score": venture_score.score,
            "risk_level": venture_score.risk_level,
            "readiness_label": venture_score.readiness_label,
            "recommendations": venture_score.recommendations,
            "ai_analysis": ai_analysis,
            "ai_error": ai_error,
            "detail_url": url_for("history.history_detail", analysis_id=analysis_id),
            "dashboard_url": url_for("dashboard.dashboard_page"),
        }
    )


def _text(value) -> str:
    """Normalize text answers from JSON."""
    return str(value or "").strip()


def _score(value) -> int:
    """Read a 1-5 score safely."""
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 3


def _build_prompt(
    *,
    idea: str,
    problem: str,
    target_audience: str,
    sector: str,
    signal: StartupSignal,
    venture_score,
) -> str:
    """Build a compact AI prompt from guided answers."""
    return f"""
Fikir: {idea}
Problem: {problem}
Hedef kitle: {target_audience or "belirtilmedi"}
Sektör: {sector or "belirtilmedi"}

Sinyaller:
- Problem aciliyeti: {signal.problem_severity}/5
- Hedef kitle netliği: {signal.target_audience_clarity}/5
- Rekabet yoğunluğu: {signal.competition_intensity}/5
- Gelir modeli netliği: {signal.monetization_clarity}/5

Venture Score: {venture_score.score}/100
Risk seviyesi: {venture_score.risk_level}
Hazırlık etiketi: {venture_score.readiness_label}

Kullanıcıya şu formatta kısa cevap ver:
1. Bu fikir ne kadar güçlü?
2. En büyük risk ne?
3. İlk yapılacak test ne olmalı?
4. Bir sonraki en mantıklı adım nedir?
"""
