"""
VentureAgent Chat modülü.

Bu, sitenin ana giriş noktasıdır: kullanıcı serbest metinle fikrini anlatabilir,
pazar araştırması isteyebilir, TR ve yurtdışı karşılaştırması yapabilir,
fikrini büyütmek için öneriler alabilir. Tek bir Claude çağrısı (multi-turn
konuşma) hem üretim hem analiz görevlerini karşılar — ayrı "agent"lara
bölünmemiştir (bkz. README, "Mimari Notlar").

Konuşma geçmişi Flask session'da (çerez) tutulur. Kalıcı/çok kullanıcılı bir
yapı için ileride veritabanına taşınabilir.
"""

from flask import Blueprint, render_template, request, jsonify, session
from backend.auth import is_pro
from backend.services.ai_client import ask_ai_conversation
from backend.services.prompts import get_prompt, get_schema
from backend.services.intent_router import classify_intent

chat_bp = Blueprint("chat", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("chat")


@chat_bp.route("/", methods=["GET"])
def chat_page():
    session.setdefault("chat_history", [])
    return render_template("chat.html", history=session["chat_history"], is_pro=is_pro())


@chat_bp.route("/message", methods=["POST"])
def send_message():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    attachments = data.get("attachments", [])
    
    if not user_message and not attachments:
        return jsonify({"error": "Mesaj veya dosya boş olamaz."}), 400

    history = session.get("chat_history", [])
    
    # We pass the full attachments to AI, but do not save them to session to avoid CookieTooLarge
    current_msg = {"role": "user", "content": user_message}
    if attachments:
        current_msg["attachments"] = attachments
        
    request_history = list(history)
    request_history.append(current_msg)

    try:
        reply = ask_ai_conversation(
            messages=request_history,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=4000,
            module="chat",
            task_complexity="medium",
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500

    # Only append text-based summary to the session history to prevent 4KB cookie limits
    history_user_msg = user_message
    if attachments:
        history_user_msg += f" [{len(attachments)} dosya eklendi]"
        
    history.append({"role": "user", "content": history_user_msg})
    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history

    intent = classify_intent(user_message, history)
    
    return jsonify({
        "reply": reply,
        "suggested_route": intent
    })


@chat_bp.route("/reset", methods=["POST"])
def reset_chat():
    session["chat_history"] = []
    return jsonify({"status": "ok"})
