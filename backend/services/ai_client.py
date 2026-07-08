"""Provider-agnostic AI client for VentureAgent."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from anthropic import Anthropic

DEFAULT_PROVIDER = "gemini"
CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

_claude_client = None


def get_ai_provider() -> str:
    """Return the selected AI provider from environment."""
    return os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def ask_ai(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    """Send a one-shot prompt to the configured AI provider."""
    provider = get_ai_provider()
    if provider == "gemini":
        return _ask_gemini(user_prompt, system_prompt, max_tokens, json_mode)
    if provider == "claude":
        return _ask_claude(user_prompt, system_prompt, max_tokens, json_mode)

    raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")


def ask_ai_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
) -> str:
    """Send a multi-turn conversation to the configured AI provider."""
    provider = get_ai_provider()
    if provider == "gemini":
        user_prompt = _format_conversation_for_gemini(messages)
        return _ask_gemini(user_prompt, system_prompt, max_tokens, json_mode=False)
    if provider == "claude":
        return _ask_claude_conversation(messages, system_prompt, max_tokens)

    raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")


def safe_parse_json(raw: str):
    """Parse AI JSON output safely after removing common markdown fences."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def _get_claude_client() -> Anthropic:
    """Create the Claude client lazily."""
    global _claude_client
    if _claude_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY tanımlı değil. .env dosyanızı kontrol edin.")
        _claude_client = Anthropic(api_key=api_key)
    return _claude_client


def _ask_claude(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    """Send a one-shot request to Claude."""
    final_system = _with_json_instruction(system_prompt, json_mode)
    response = _get_claude_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=final_system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def _ask_claude_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
) -> str:
    """Send a multi-turn conversation to Claude."""
    response = _get_claude_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def _ask_gemini(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
) -> str:
    """Send a one-shot request to Gemini using the REST API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil. .env dosyanızı kontrol edin.")

    final_prompt = user_prompt
    if json_mode:
        final_prompt += (
            "\n\nSADECE geçerli JSON döndür. Başka hiçbir açıklama, markdown işareti "
            "veya ``` kullanma."
        )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": final_prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {
                "thinkingBudget": 0,
            },
        },
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_prompt},
            ]
        }

    request = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API hata döndürdü: {exc.code} - {details}") from exc

    return _extract_gemini_text(data)


def _extract_gemini_text(data: dict) -> str:
    """Extract text from Gemini generateContent response."""
    for candidate in data.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if part.get("text")]
        if texts:
            return "\n".join(texts)

    raise RuntimeError("Gemini cevabında metin bulunamadı.")


def _format_conversation_for_gemini(messages: list[dict]) -> str:
    """Flatten Flask session chat history into one Gemini prompt."""
    lines = []
    for message in messages:
        role = "Kullanıcı" if message.get("role") == "user" else "Asistan"
        lines.append(f"{role}: {message.get('content', '')}")
    lines.append("Asistan:")
    return "\n".join(lines)


def _with_json_instruction(system_prompt: str, json_mode: bool) -> str:
    """Append strict JSON instruction when needed."""
    if not json_mode:
        return system_prompt

    return (
        system_prompt
        + "\n\nSADECE geçerli JSON döndür. Başka hiçbir açıklama, markdown işareti veya ``` kullanma."
    )
