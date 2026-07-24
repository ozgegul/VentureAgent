"""Provider-agnostic AI client for VentureAgent.

Phase 4 enhancements:
- 4a: Retry with exponential backoff for transient errors (429, 500, 502, 503)
- 4b: Robust ``safe_parse_json`` with JSON extraction and schema validation
- 4c: Dynamic ``thinkingBudget`` per task complexity via ``_build_gemini_config``
- 4d: Proper Gemini multi-turn conversation using ``contents`` array
- Integrated observability via ``ai_logger``

Phase 5 enhancements:
- ``ask_ai()`` signature extended with ``task_complexity`` for complexity-aware
  Gemini configuration.  All new parameters have defaults so existing callers
  continue to work unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

from anthropic import Anthropic

from backend.services.ai_logger import log_ai_call

logger = logging.getLogger("ventureagent.ai")

DEFAULT_PROVIDER = "gemini"
CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

_claude_client = None

# Transient HTTP status codes that are safe to retry.
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503})
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_ai_provider() -> str:
    """Return the selected AI provider from environment."""
    return os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def ask_ai(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
    module: str = "unknown",
    task_complexity: str = "low",
    response_schema: dict | None = None,
) -> str:
    """Send a one-shot prompt to the configured AI provider.

    Parameters
    ----------
    module:
        Name of the calling module (e.g. ``"swot"``, ``"chat"``).  Used for
        logging only — callers that do not pass it default to ``"unknown"``.
    task_complexity:
        One of ``"low"``, ``"medium"``, or ``"high"``.  Controls the Gemini
        ``thinkingBudget`` (0 / 1024 / 4096 respectively).  Has no effect
        when the Claude provider is active.  Defaults to ``"low"``.
    response_schema:
        Optional dict whose **keys** are required top-level JSON keys and
        **values** are expected Python types.  When provided together with
        ``json_mode=True``, the raw response is automatically parsed and
        validated via ``safe_parse_json`` before being returned as a string.
        This gives callers early, descriptive errors instead of silent
        template breakage.
    """
    provider = get_ai_provider()
    start = time.monotonic()
    prompt_len = len(user_prompt) + len(system_prompt)
    try:
        if provider == "gemini":
            result = _ask_gemini(user_prompt, system_prompt, max_tokens, json_mode, task_complexity)
        elif provider == "claude":
            result = _ask_claude(user_prompt, system_prompt, max_tokens, json_mode)
        else:
            raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")

        # Validate JSON structure early when a schema is provided.
        # This doesn't change the return type (still str) but ensures the
        # response is parseable and contains the expected keys *before*
        # the caller tries to use it.
        if json_mode and response_schema:
            safe_parse_json(result, schema=response_schema)

    except Exception:
        latency_ms = int((time.monotonic() - start) * 1000)
        log_ai_call(
            provider=provider,
            module=module,
            prompt_len=prompt_len,
            response_len=0,
            latency_ms=latency_ms,
            success=False,
        )
        raise

    latency_ms = int((time.monotonic() - start) * 1000)
    log_ai_call(
        provider=provider,
        module=module,
        prompt_len=prompt_len,
        response_len=len(result),
        latency_ms=latency_ms,
        success=True,
    )
    return result


def ask_ai_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
    module: str = "chat",
) -> str:
    """Send a multi-turn conversation to the configured AI provider."""
    provider = get_ai_provider()
    prompt_len = sum(len(m.get("content", "")) for m in messages) + len(system_prompt)
    start = time.monotonic()
    try:
        if provider == "gemini":
            result = _ask_gemini_conversation(messages, system_prompt, max_tokens)
        elif provider == "claude":
            result = _ask_claude_conversation(messages, system_prompt, max_tokens)
        else:
            raise RuntimeError("AI_PROVIDER değeri 'gemini' veya 'claude' olmalı.")
    except Exception:
        latency_ms = int((time.monotonic() - start) * 1000)
        log_ai_call(
            provider=provider,
            module=module,
            prompt_len=prompt_len,
            response_len=0,
            latency_ms=latency_ms,
            success=False,
        )
        raise

    latency_ms = int((time.monotonic() - start) * 1000)
    log_ai_call(
        provider=provider,
        module=module,
        prompt_len=prompt_len,
        response_len=len(result),
        latency_ms=latency_ms,
        success=True,
    )
    return result


# ---------------------------------------------------------------------------
# 4b: Robust JSON parsing with schema validation
# ---------------------------------------------------------------------------


def safe_parse_json(raw: str, schema: dict | None = None):
    """Parse AI JSON output safely with optional schema validation.

    Handles common LLM output issues:
    - Markdown code fences (````` json ...  ```````)
    - Leading/trailing non-JSON text
    - Missing required top-level keys (when *schema* is provided)

    Parameters
    ----------
    raw:
        The raw text returned by the LLM.
    schema:
        An optional dict whose **keys** are the required top-level keys and
        whose **values** are the expected Python types (e.g.
        ``{"strengths": list, "weaknesses": list}``).  When provided, a
        ``ValueError`` is raised if any key is missing or has the wrong type.
    """
    # Step 1: strip markdown fences
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    # Step 2: if the result doesn't start with '{' or '[', try to extract
    #         the JSON object/array from surrounding text
    if cleaned and cleaned[0] not in ("{", "["):
        obj_start = cleaned.find("{")
        arr_start = cleaned.find("[")
        # Pick whichever comes first (ignoring -1 = not found)
        starts = [s for s in (obj_start, arr_start) if s >= 0]
        if starts:
            start = min(starts)
            # Find matching close bracket
            open_char = cleaned[start]
            close_char = "}" if open_char == "{" else "]"
            end = cleaned.rfind(close_char)
            if end > start:
                cleaned = cleaned[start : end + 1]

    parsed = json.loads(cleaned)

    # Step 3: validate against schema if provided
    if schema and isinstance(parsed, dict):
        _validate_schema(parsed, schema)

    return parsed


def _validate_schema(data: dict, schema: dict) -> None:
    """Ensure all required top-level keys exist and have the right type."""
    missing = set(schema.keys()) - set(data.keys())
    if missing:
        raise ValueError(f"AI yanıtında eksik alanlar: {missing}")

    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            raise ValueError(
                f"AI yanıtında '{key}' alanı {expected_type.__name__} olmalı, "
                f"ancak {type(data[key]).__name__} geldi."
            )


# ---------------------------------------------------------------------------
# 4a: Retry helper with exponential backoff
# ---------------------------------------------------------------------------


def _retry(fn, *, max_retries: int = _MAX_RETRIES, base_delay: float = _RETRY_BASE_DELAY):
    """Execute *fn* with exponential-backoff retries on transient errors.

    Only HTTP status codes in ``_RETRYABLE_STATUS_CODES`` and generic
    ``ConnectionError`` / ``TimeoutError`` are retried.  All other exceptions
    propagate immediately.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRYABLE_STATUS_CODES:
                raise  # client error — don't retry
            last_exc = exc
        except (ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc

        delay = base_delay * (2 ** attempt)
        logger.warning(
            "Transient error (attempt %d/%d), retrying in %.1fs: %s",
            attempt + 1,
            max_retries,
            delay,
            last_exc,
        )
        time.sleep(delay)

    # All retries exhausted — re-raise the last exception
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Claude helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


_THINKING_BUDGETS: dict[str, int] = {"low": 0, "medium": 1024, "high": 4096}


def _build_gemini_config(max_tokens: int, task_complexity: str = "low") -> dict:
    """Build a Gemini ``generationConfig`` with dynamic ``thinkingBudget``.

    Parameters
    ----------
    max_tokens:
        Maximum output tokens for the response.
    task_complexity:
        One of ``"low"``, ``"medium"``, or ``"high"``.  Maps to
        ``thinkingBudget`` values 0, 1024, and 4096 respectively.
        Unknown values fall back to 0 (no thinking).
    """
    return {
        "temperature": 0.4,
        "maxOutputTokens": max_tokens,
        "thinkingConfig": {
            "thinkingBudget": _THINKING_BUDGETS.get(task_complexity, 0),
        },
    }


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
        "generationConfig": _build_gemini_config(max_tokens, task_complexity),
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_prompt},
            ]
        }

    return _send_gemini_request(api_key, payload)


def _ask_gemini_conversation(
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int = 1200,
) -> str:
    """Send a proper multi-turn conversation to Gemini.

    Uses the Gemini ``contents`` array with ``user`` / ``model`` roles
    instead of the old string-concatenation approach that lost role
    boundaries.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil. .env dosyanızı kontrol edin.")

    contents: list[dict] = []
    for msg in messages:
        role = "user" if msg.get("role") == "user" else "model"
        parts = []
        if msg.get("content"):
            parts.append({"text": msg.get("content")})
        
        for att in msg.get("attachments", []):
            parts.append({
                "inlineData": {
                    "mimeType": att["mime_type"],
                    "data": att["data"]
                }
            })
            
        contents.append({"role": role, "parts": parts})

    payload: dict = {
        "contents": contents,
        "generationConfig": _build_gemini_config(max_tokens, "medium"),
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_prompt},
            ]
        }

    return _send_gemini_request(api_key, payload)


def _send_gemini_request(api_key: str, payload: dict) -> str:
    """Send a payload to the Gemini REST endpoint with retry logic.

    Shared by both one-shot and conversation Gemini helpers.
    """

    def _call():
        req = urllib.request.Request(
            GEMINI_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = _retry(_call)
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


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def _with_json_instruction(system_prompt: str, json_mode: bool) -> str:
    """Append strict JSON instruction when needed."""
    if not json_mode:
        return system_prompt

    return (
        system_prompt
        + "\n\nSADECE geçerli JSON döndür. Başka hiçbir açıklama, markdown işareti veya ``` kullanma."
    )
