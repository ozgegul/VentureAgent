"""Provider-agnostic AI client for VentureAgent."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import logging

import anthropic
from anthropic import Anthropic
from backend.services.ai_logger import log_ai_call

DEFAULT_PROVIDER = "gemini"
CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

_claude_client = None


def get_ai_provider() -> str:
    """Return the selected AI provider from environment."""
    return os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def _retry(fn, max_retries=3, base_delay=1.0):
    """Retry with exponential backoff for transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (urllib.error.HTTPError, ConnectionError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            
            status_code = getattr(e, 'code', getattr(e, 'status_code', None))
            if status_code is not None and status_code not in (429, 500, 502, 503, 529):
                raise  # Don't retry client errors
            time.sleep(base_delay * (2 ** attempt))


def ask_ai(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
    module: str = "unknown",
    task_complexity: str = "low",
    response_schema: dict | None = None
) -> str:
    """Send a one-shot prompt to the configured AI provider."""
    start_time = time.time()
    provider = get_ai_provider()
    success = False
    response = ""
    
    try:
        if provider == "gemini":
            response = _ask_gemini(user_prompt, system_prompt, max_tokens, json_mode, task_complexity)
        elif provider == "claude":
            response = _ask_claude(user_prompt, system_prompt, max_tokens, json_mode)
        else:
            raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")
            
        success = True
        return response
    except (urllib.error.HTTPError, anthropic.APIStatusError) as e:
        status_code = getattr(e, 'code', getattr(e, 'status_code', None))
        if status_code in (429, 503, 529):
            raise RuntimeError("Yapay zeka sunucuları şu anda yoğun. Lütfen daha sonra tekrar deneyin.") from e
        raise RuntimeError(f"Yapay zeka sağlayıcısından hata alındı (Kod: {status_code}).") from e
    except (ConnectionError, anthropic.APIConnectionError) as e:
        raise RuntimeError("Yapay zeka sunucularına bağlanılamadı. Lütfen internet bağlantınızı kontrol edin.") from e
    finally:
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_len = len(user_prompt) + len(system_prompt)
        response_len = len(response) if response else 0
        log_ai_call(provider=provider, module=module, prompt_len=prompt_len, response_len=response_len, latency_ms=latency_ms, success=success)


def ask_ai_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
    module: str = "unknown",
    task_complexity: str = "low",
) -> str:
    """Send a multi-turn conversation to the configured AI provider."""
    start_time = time.time()
    provider = get_ai_provider()
    success = False
    response = ""

    try:
        if provider == "gemini":
            response = _ask_gemini_conversation(messages, system_prompt, max_tokens, task_complexity)
        elif provider == "claude":
            response = _ask_claude_conversation(messages, system_prompt, max_tokens)
        else:
            raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")
            
        success = True
        return response
    except (urllib.error.HTTPError, anthropic.APIStatusError) as e:
        status_code = getattr(e, 'code', getattr(e, 'status_code', None))
        if status_code in (429, 503, 529):
            raise RuntimeError("Yapay zeka sunucuları şu anda yoğun. Lütfen daha sonra tekrar deneyin.") from e
        raise RuntimeError(f"Yapay zeka sağlayıcısından hata alındı (Kod: {status_code}).") from e
    except (ConnectionError, anthropic.APIConnectionError) as e:
        raise RuntimeError("Yapay zeka sunucularına bağlanılamadı. Lütfen internet bağlantınızı kontrol edin.") from e
    finally:
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_len = sum(len(m.get("content", "")) for m in messages) + len(system_prompt)
        response_len = len(response) if response else 0
        log_ai_call(provider=provider, module=module, prompt_len=prompt_len, response_len=response_len, latency_ms=latency_ms, success=success)


def safe_parse_json(raw: str, schema: dict | None = None):
    """Parse and optionally validate AI JSON output."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    
    # Try to fix common LLM JSON errors
    if not cleaned.startswith("{"):
        # Extract JSON from surrounding text
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]
    
    parsed = json.loads(cleaned)
    
    if schema:
        _validate_keys(parsed, schema)
    
    return parsed


def _validate_keys(data: dict, schema: dict) -> None:
    """Ensure all required top-level keys exist."""
    missing = set(schema.keys()) - set(data.keys())
    if missing:
        raise ValueError(f"AI yanıtında eksik alanlar: {missing}")


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
    
    def _call():
        return _get_claude_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=final_system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        
    response = _retry(_call)
    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def _ask_claude_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
) -> str:
    """Send a multi-turn conversation to Claude."""
    def _call():
        return _get_claude_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        
    response = _retry(_call)
    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def _build_gemini_config(max_tokens: int, task_complexity: str = "low", json_mode: bool = False) -> dict:
    thinking_budgets = {"low": 0, "medium": 1024, "high": 4096}
    budget = thinking_budgets.get(task_complexity, 0)
    config = {
        "temperature": 0.4,
        "maxOutputTokens": max_tokens,
    }
    if budget > 0:
        config["thinkingConfig"] = {"thinkingBudget": budget}
    if json_mode:
        config["responseMimeType"] = "application/json"
    return config


def _ask_gemini(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
    task_complexity: str = "low",
) -> str:
    """Send a one-shot request to Gemini using the REST API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil. .env dosyanızı kontrol edin.")

    # Prevent JSON cut-off by ensuring a safe token limit
    if json_mode and max_tokens < 4000:
        max_tokens = 4000

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
        "generationConfig": _build_gemini_config(max_tokens, task_complexity, json_mode),
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

    def _call():
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
        return _extract_gemini_text(data)

    return _retry(_call)


def _ask_gemini_conversation(messages: list[dict], system_prompt: str, max_tokens: int, task_complexity: str = "low") -> str:
    """Send proper multi-turn conversation to Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil. .env dosyanızı kontrol edin.")
        
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        parts = []
        if msg.get("content"):
            parts.append({"text": msg["content"]})
        if "attachments" in msg:
            for att in msg["attachments"]:
                parts.append({
                    "inlineData": {
                        "mimeType": att["mimeType"],
                        "data": att["data"]
                    }
                })
        contents.append({"role": role, "parts": parts})
    
    payload = {
        "contents": contents,
        "generationConfig": _build_gemini_config(max_tokens, task_complexity, False),
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        
    request = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    def _call():
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
        return _extract_gemini_text(data)

    return _retry(_call)


def _extract_gemini_text(data: dict) -> str:
    """Extract text from Gemini generateContent response."""
    for candidate in data.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if part.get("text")]
        if texts:
            return "\n".join(texts)

    raise RuntimeError("Gemini cevabında metin bulunamadı.")


def _with_json_instruction(system_prompt: str, json_mode: bool) -> str:
    """Append strict JSON instruction when needed."""
    if not json_mode:
        return system_prompt

    return (
        system_prompt
        + "\n\nSADECE geçerli JSON döndür. Başka hiçbir açıklama, markdown işareti veya ``` kullanma."
    )
