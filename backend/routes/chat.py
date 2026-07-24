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

import base64
from flask import Blueprint, render_template, request, jsonify, session, url_for
from backend.services.ai_client import ask_ai_conversation
from backend.services.intent_router import classify_intent
from backend.services.prompts import get_prompt

chat_bp = Blueprint("chat", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = get_prompt("chat")


@chat_bp.route("/", methods=["GET"])
def chat_page():
    session.setdefault("chat_history", [])
    return render_template("chat.html", history=session["chat_history"])


@chat_bp.route("/message", methods=["POST"])
def send_message():
    # Handle both JSON (fallback) and multipart/form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()
    else:
        user_message = request.form.get("message", "").strip()

    if not user_message and not request.files:
        return jsonify({"error": "Mesaj veya dosya boş olamaz."}), 400

    attachments = []
    
    file_upload = request.files.get("file")
    if file_upload and file_upload.filename:
        file_data = file_upload.read()
        b64_data = base64.b64encode(file_data).decode("utf-8")
        attachments.append({
            "mime_type": file_upload.mimetype or "application/octet-stream",
            "data": b64_data,
            "filename": file_upload.filename
        })
        
    audio_upload = request.files.get("audio")
    if audio_upload:
        audio_data = audio_upload.read()
        b64_data = base64.b64encode(audio_data).decode("utf-8")
        attachments.append({
            "mime_type": audio_upload.mimetype or "audio/webm",
            "data": b64_data,
            "filename": "Ses Kaydı"
        })

    history = session.get("chat_history", [])
    
    # Construct the user message object for the AI
    current_turn = {"role": "user", "content": user_message}
    if attachments:
        current_turn["attachments"] = attachments
        
    # We append the full turn with attachments to a *copy* of the history
    # because we cannot save base64 data to the Flask session cookie (4KB limit).
    ai_history = history.copy()
    ai_history.append(current_turn)

    try:
        reply = ask_ai_conversation(
            messages=ai_history,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=2500,
            module="chat",
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500

    # For the session history, we strip the heavy base64 attachments 
    # and add a text indicator.
    session_turn = {"role": "user", "content": user_message}
    if attachments:
        file_names = ", ".join([a["filename"] for a in attachments])
        session_turn["content"] = f"{user_message}\n\n[Ekli Dosya(lar): {file_names}]".strip()
        
    history.append(session_turn)
    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history
    
    # Phase 2: After getting the AI reply, check for routing opportunity
    intent = classify_intent(user_message, history[:-1]) # exclude the assistant's reply just added

    response = {"reply": reply}
    if intent.intent != "chat" and intent.confidence > 0.7:
        # Some intents like 'idea' map to 'idea.idea_form'. Let's ensure robust url_for mapping.
        # The route functions are named like `{module}.{module}_form` for most, but swot is swot.swot_form, competitors is competitors.competitors_form. Let's check them.
        try:
            form_endpoint = f"{intent.intent}.{intent.intent}_form"
            response["suggestion"] = {
                "module": intent.intent,
                "url": url_for(form_endpoint),
                "text": intent.suggestion_text,
                "prefill_idea": intent.extracted_idea,
            }
        except Exception as e:
            print(f"Failed to build url for intent {intent.intent}: {e}")

    return jsonify(response)


@chat_bp.route("/reset", methods=["POST"])
def reset_chat():
    session["chat_history"] = []
    return jsonify({"status": "ok"})
