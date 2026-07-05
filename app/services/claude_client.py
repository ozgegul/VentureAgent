"""
Anthropic Claude API ile konuşan merkezi servis.
Tüm blueprint'ler (routes/) bu modülü kullanır.

ÖNEMLİ: API anahtarı sadece burada, sunucu tarafında kullanılır.
Asla template'lere (frontend) veya static/js dosyalarına taşımayın.
"""

import os
import json
from anthropic import Anthropic

MODEL = "claude-sonnet-5"  # Analiz/SWOT/roadmap gibi akıl yürütme gerektiren görevler için

_client = None


def get_client() -> Anthropic:
    """Anthropic client'ı lazy şekilde oluşturur (tek instance)."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY tanımlı değil. .env dosyanızı kontrol edin."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def ask_claude(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    """
    Claude'a tek seferlik bir istek gönderir ve metin cevabını döner.

    json_mode=True verilirse, modelden sadece geçerli JSON döndürmesi istenir
    (SWOT, Kanban kartları gibi yapılandırılmış veriler için kullanışlıdır).
    """
    client = get_client()

    final_system = system_prompt
    if json_mode:
        final_system += (
            "\n\nSADECE geçerli JSON döndür. Başka hiçbir açıklama, "
            "markdown işareti veya ``` kullanma."
        )

    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=final_system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def ask_claude_conversation(
    messages: list,
    system_prompt: str = "",
    max_tokens: int = 1200,
) -> str:
    """
    Çok turlu (multi-turn) konuşma için Claude'a istek gönderir.
    `messages`, [{"role": "user"|"assistant", "content": "..."}] formatında olmalı.
    Konuşma geçmişi çağıran taraf (route) tarafından yönetilir — bu fonksiyon
    stateless'tır, her seferinde tüm geçmişi alır.
    """
    client = get_client()

    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def safe_parse_json(raw: str):
    """json_mode=True ile gelen cevabı güvenli şekilde parse eder."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)
