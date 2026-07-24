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
from backend.auth import current_user, is_pro
from backend.services.ai_client import ask_ai_conversation

chat_bp = Blueprint("chat", __name__, template_folder="../../frontend/templates")

SYSTEM_PROMPT = """Sen VentureAgent'sın — girişimcilerin fikir ortağı
gibi davranan bir yapay zekasın. Görevin:

1. Girişim fikirlerini sorgulamak ve netleştirmek (doğru sorular sorarak)
2. Pazar araştırması yapmak (sektör büyüklüğü, trendler, potansiyel)
3. Türkiye ve yurtdışı (özellikle ABD/Avrupa) pazarlarını karşılaştırmak —
   farklılıkları, fırsatları ve riskleri somut şekilde belirtmek
4. Fikirleri büyütmek için yeni açılar, özellikler veya pivot önerileri üretmek
5. Gerektiğinde SWOT, rakip analizi, gelir modeli, roadmap gibi daha
   yapılandırılmış çıktılar için sitenin ilgili modülüne yönlendirmek

Kısa, net ve uygulanabilir cevaplar ver. Genel geçer motivasyon cümleleri
kurma; somut veri, örnek ve aksiyon öner. Türkçe konuş. Emin olmadığın güncel
sayısal veriler (pazar büyüklüğü, yatırım rakamları vb.) için tahmini
olduğunu belirt, uydurma kesin rakam verme."""


@chat_bp.route("/", methods=["GET"])
def chat_page():
    session.setdefault("chat_history", [])
    return render_template("chat.html", history=session["chat_history"], is_pro=is_pro())


@chat_bp.route("/message", methods=["POST"])
def send_message():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    attachment = data.get("attachment")
    use_voice = bool(data.get("voice"))

    is_pro_user = is_pro()
    if attachment and not is_pro_user:
        return jsonify({"error": "Dosya yükleme yalnızca Pro/Admin kullanıcılar için kullanılabilir."}), 403
    if use_voice and not is_pro_user:
        return jsonify({"error": "Sesli yanıt yalnızca Pro/Admin kullanıcılar için kullanılabilir."}), 403

    if attachment and isinstance(attachment, dict):
        file_name = attachment.get("name", "dosya")
        file_content = (attachment.get("content") or "").strip()
        is_image = bool(attachment.get("is_image"))

        if is_image:
            metadata = [
                f"Dosya: {file_name}",
                f"Tür: {attachment.get('type', 'image')}",
                f"Boyut: {attachment.get('size', 0)} bytes",
            ]
            attachment_text = "\n".join(metadata)
        elif file_content:
            if len(file_content) > 3000:
                file_content = file_content[:3000] + "\n\n... (dosya içeriği kısaltıldı)"
            attachment_text = f"{file_content}"
        else:
            attachment_text = None

        if attachment_text:
            user_message = (
                f"{user_message}\n\n[Eklenti: {file_name}]\n{attachment_text}"
                if user_message
                else f"[Eklenti: {file_name}]\n{attachment_text}"
            )

    if not user_message:
        return jsonify({"error": "Mesaj boş olamaz."}), 400

    history = session.get("chat_history", [])
    history.append({"role": "user", "content": user_message})

    try:
        reply = ask_ai_conversation(
            messages=history,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=1200,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500

    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history

    return jsonify({"reply": reply})


@chat_bp.route("/reset", methods=["POST"])
def reset_chat():
    session["chat_history"] = []
    return jsonify({"status": "ok"})
