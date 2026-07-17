"""Guided chat-first idea analysis flow."""

from __future__ import annotations

import uuid
import re

from flask import Blueprint, jsonify, render_template, request, session, url_for

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
    session.pop("guided_state", None)
    return render_template("guided.html")


@guided_bp.route("/message", methods=["POST"])
def guided_message():
    """Handle one adaptive guided chat message."""
    data = request.get_json(silent=True) or {}
    message = _text(data.get("message"))
    location = _text(data.get("location"))
    if not message:
        return jsonify({"error": "Mesaj boş olamaz."}), 400

    state = session.get("guided_state") or {}
    session_id = _get_or_create_session_id()

    if state.get("analysis_done"):
        result = _continue_guided_conversation(message=message, state=state)
        followups = state.get("followups", [])
        followups.append({"user": message, "assistant": result["reply"]})
        state["followups"] = followups[-6:]
        session["guided_state"] = state
        return jsonify(result)

    if state.get("idea") and not state.get("location"):
        location = message
        idea = state["idea"]
    else:
        idea = message
        location = location or _extract_location(message)

    if not location:
        session["guided_state"] = {"idea": idea}
        return jsonify(
            {
                "reply": (
                    "Fikir güzel görünüyor. Bölgesel fırsatları ve riskleri "
                    "hesaplayabilmem için bunu hangi şehir, ilçe veya bölgede yapmak istiyorsun?"
                ),
                "done": False,
                "awaiting_location": True,
            }
        )

    state = {
        "idea": idea,
        "location": location,
    }
    result = _build_location_analysis(
        idea=state["idea"],
        location=state["location"],
        session_id=session_id,
    )
    state["analysis_done"] = True
    state["last_analysis"] = result["reply"]
    state["score"] = result["score"]
    state["risk_level"] = result["risk_level"]
    state["readiness_label"] = result["readiness_label"]
    state["detail_url"] = result["detail_url"]
    state["history_url"] = result["history_url"]
    session["guided_state"] = state
    return jsonify(result)


@guided_bp.route("/analyze", methods=["POST"])
def analyze_guided():
    """Analyze guided answers, save them, and return a compact result."""
    data = request.get_json(silent=True) or {}
    session_id = _get_or_create_session_id()

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
        ai_analysis = _build_fallback_analysis(
            idea=idea,
            problem=problem,
            target_audience=target_audience,
            sector=sector,
            venture_score=venture_score,
        )

    analysis_id = save_idea_analysis(
        idea=idea,
        problem=problem,
        target_audience=target_audience,
        sector=sector,
        signal=signal,
        venture_score=venture_score,
        ai_analysis=ai_analysis,
        session_id=session_id,
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
            "detail_url": url_for("public_history.public_history_latest"),
            "history_url": url_for("public_history.public_history_page"),
        }
    )


def _get_or_create_session_id() -> str:
    """Keep one anonymous browser session id for user-owned results."""
    if not session.get("visitor_id"):
        session["visitor_id"] = uuid.uuid4().hex
    return session["visitor_id"]


def _extract_location(message: str) -> str:
    """Extract an explicitly written location without forcing another question."""
    location_match = re.search(
        r"\b([A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ-]*(?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ-]*){0,2})"
        r"(?:'|’)?(?:da|de|ta|te)\b",
        message,
    )
    if location_match:
        return location_match.group(1)

    try:
        extracted = ask_ai(
            user_prompt=(
                "Aşağıdaki girişim fikrinde açıkça yazılmış şehir, ilçe veya bölgeyi "
                "yalnızca yer adı olarak döndür. Lokasyon yoksa sadece YOK yaz.\n\n"
                f"Metin: {message}"
            ),
            system_prompt="Yalnızca yer adı veya YOK cevabı ver.",
            max_tokens=40,
        ).strip().strip("*# `")
    except Exception:
        return ""

    if not extracted or extracted.upper() == "YOK":
        return ""
    return extracted.splitlines()[0].strip()


def _build_location_analysis(*, idea: str, location: str, session_id: str) -> dict:
    """Create a location-aware analysis from a short chat."""
    signal = StartupSignal(
        problem_severity=4,
        target_audience_clarity=3,
        competition_intensity=3,
        monetization_clarity=3,
    )
    venture_score = build_venture_score(signal)

    ai_error = None
    try:
        ai_analysis = ask_ai(
            user_prompt=f"""
Kullanıcının fikri: {idea}
Lokasyon bilgisi: {location}

Bu fikri tam olarak verilen lokasyona göre değerlendir. Kesin veri uydurma;
emin olmadığın yerlerde "yerel araştırmayla doğrulanmalı" de. Türkçe, çok kısa
ve kolay taranabilir yaz. Markdown işaretleri (*, **, #) kullanma. Her başlık
altında en fazla 2 kısa cümle olsun. Tekrar etme.

Şu başlıklarla cevap ver:
1. Fırsat
2. En önemli 3 risk
3. Risk seviyesi ve kısa gerekçesi
4. {location} içinde başlangıç noktası
5. İlk 3 adım
""",
            system_prompt=SYSTEM_PROMPT,
            max_tokens=900,
        )
    except Exception as exc:  # noqa: BLE001
        ai_error = str(exc)
        ai_analysis = _build_location_fallback(
            idea=idea,
            location=location,
            venture_score=venture_score,
        )

    analysis_id = save_idea_analysis(
        idea=idea,
        problem=f"{location} lokasyonunda doğrulanacak kullanıcı ihtiyacı",
        target_audience=f"{location} içindeki potansiyel kullanıcılar",
        sector="Belirtilmedi",
        signal=signal,
        venture_score=venture_score,
        ai_analysis=ai_analysis,
        session_id=session_id,
    )

    return {
        "reply": ai_analysis,
        "done": True,
        "id": analysis_id,
        "score": venture_score.score,
        "risk_level": venture_score.risk_level,
        "readiness_label": venture_score.readiness_label,
        "recommendations": venture_score.recommendations,
        "ai_analysis": ai_analysis,
        "ai_error": ai_error,
        "detail_url": url_for("public_history.public_history_latest"),
        "history_url": url_for("public_history.public_history_page"),
    }


def _continue_guided_conversation(*, message: str, state: dict) -> dict:
    """Answer follow-up questions after the first analysis is complete."""
    idea = state.get("idea", "")
    location = state.get("location", "")
    previous_analysis = state.get("last_analysis", "")
    followup_history = "\n".join(
        f"Kullanıcı: {item.get('user', '')}\nVentureAgent: {item.get('assistant', '')}"
        for item in state.get("followups", [])[-4:]
    )

    try:
        reply = ask_ai(
            user_prompt=f"""
Kullanıcının fikri: {idea}
Lokasyon: {location}
Önceki analiz:
{previous_analysis}

Son konuşma geçmişi:
{followup_history or "Henüz takip sorusu yok."}

Kullanıcının devam sorusu:
{message}

Bu soruya önceki analize dayanarak cevap ver. Kullanıcı "neden olmaz",
"nasıl olur", "başka nerede olur" gibi sorular sorabilir. Kesin veri uydurma;
emin olmadığın yerlerde yerel araştırmayla doğrulanmalı de. Türkçe, pratik ve
kısa cevap ver.
""",
            system_prompt=SYSTEM_PROMPT,
            max_tokens=700,
        )
    except Exception:
        reply = _build_followup_fallback(message=message, state=state)

    return {
        "reply": reply,
        "done": False,
        "analysis_ready": True,
        "detail_url": state.get("detail_url"),
        "history_url": state.get("history_url"),
    }


def _build_followup_fallback(*, message: str, state: dict) -> str:
    """Local follow-up answer when the AI provider is unavailable."""
    location = state.get("location", "bu lokasyon")
    idea = state.get("idea", "bu fikir")
    lower_message = message.lower()

    if "neden" in lower_message or "olmaz" in lower_message:
        return (
            f"{idea} için {location} içinde zorlanabilecek noktalar şunlar olabilir: "
            "hedef kitlenin problemi yeterince sık yaşamaması, benzer çözümlerin zaten "
            "kullanılıyor olması, ödeme isteğinin düşük kalması veya doğru bölgenin "
            "seçilmemesi. Bunu anlamak için önce 10 kullanıcı görüşmesi ve küçük bir "
            "ön kayıt testi yapmak iyi olur."
        )

    if "nasıl" in lower_message:
        return (
            f"{location} için en pratik yol küçük başlamaktır: önce 2-3 bölge seç, "
            "her bölgede hedef kullanıcılarla kısa görüşmeler yap, en güçlü talep gelen "
            "yerde basit bir MVP veya ön kayıt sayfası dene. Sonra ilgi, geri dönüş ve "
            "ödeme isteğini karşılaştır."
        )

    if "nerede" in lower_message or "başka" in lower_message or "baska" in lower_message:
        return (
            f"{location} dışında benzer kullanıcı yoğunluğu olan yakın ilçeler, merkezi "
            "caddeler, üniversite çevreleri, işletme yoğunluğu olan bölgeler veya toplu "
            "taşıma aksları denenebilir. En doğru seçim için rakip yoğunluğu ve hedef "
            "kullanıcı trafiği yerelde kontrol edilmeli."
        )

    return (
        "Bunu mevcut analiz üzerinden netleştirmek için en iyi sonraki adım, varsayımı "
        "tek cümleye indirip küçük bir test yapmaktır: kim, hangi problemi, ne sıklıkta "
        "yaşıyor ve çözüm için ne kadar istekli?"
    )


def _build_location_fallback(*, idea: str, location: str, venture_score) -> str:
    """Local location-aware response when the AI provider is unavailable."""
    recommendations = "\n".join(
        f"- {recommendation}" for recommendation in venture_score.recommendations
    )
    return f"""AI sağlayıcısı şu anda yanıt veremediği için yerel değerlendirme gösteriliyor.

Fikir: {idea}
Lokasyon: {location}

1. Nerelerde denenebilir?
Önce {location} içinde insan yoğunluğunun ve tekrar ziyaretin yüksek olduğu merkezleri düşün: merkezi caddeler, üniversite/okul çevreleri, toplu taşıma noktaları, alışveriş alanları ve mahalle merkezleri.

2. Hangi bölgelerde fırsat olabilir?
Fırsat, rakibin az olduğu ama hedef kullanıcının düzenli bulunduğu yerlerde çıkar. Bu yüzden aynı fikri hem yoğun merkezde hem de daha az hizmet alan bir bölgede küçük testle karşılaştırmak iyi olur.

3. Hangi eksikler araştırılmalı?
Bu fikre benzer çözümler var mı, kullanıcılar şu an problemi nasıl çözüyor, ödeme isteği var mı ve lokasyonda erişim kolay mı soruları doğrulanmalı.

4. İlk doğrulama adımları
- {location} içinde 2-3 olası bölge seç.
- Her bölgede 5-10 hedef kullanıcıyla kısa görüşme yap.
- En güçlü talebin geldiği bölgede küçük bir MVP veya ön kayıt testi dene.

Venture Score: {venture_score.score}/100
Risk seviyesi: {venture_score.risk_level}
Sonraki öneriler:
{recommendations}"""


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


def _build_fallback_analysis(
    *,
    idea: str,
    problem: str,
    target_audience: str,
    sector: str,
    venture_score,
) -> str:
    """Build a local analysis when the external AI provider is unavailable."""
    recommendations = "\n".join(
        f"- {recommendation}" for recommendation in venture_score.recommendations
    )
    return f"""AI sağlayıcısı şu anda yanıt veremediği için yerel değerlendirme gösteriliyor.

1. Bu fikir ne kadar güçlü?
Venture Score {venture_score.score}/100. Hazırlık durumu: {venture_score.readiness_label}.

2. En büyük risk ne?
Risk seviyesi: {venture_score.risk_level}. En kritik nokta, problemi ve hedef kitleyi gerçek kullanıcı görüşmeleriyle doğrulamak.

3. İlk yapılacak test ne olmalı?
{target_audience or "Hedef kullanıcı"} içinden 5-10 kişiyle görüşüp şu problemi gerçekten yaşayıp yaşamadıklarını ölç: {problem}

4. Bir sonraki en mantıklı adım nedir?
{recommendations}

Fikir: {idea}
Sektör: {sector or "Belirtilmedi"}"""
