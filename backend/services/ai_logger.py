"""AI call observability and free-tier quota tracking for VentureAgent.

Every call to ``ask_ai`` / ``ask_ai_conversation`` is logged with provider,
module name, character counts, latency, and success/failure status.

An in-memory daily counter tracks API usage against the free-tier limit
(conservative 450 of 500 RPD for Gemini) and emits a WARNING when the
remaining budget drops below 50 calls.
"""

from __future__ import annotations

import logging
import time
from datetime import date

logger = logging.getLogger("ventureagent.ai")

# ---------------------------------------------------------------------------
# Daily quota tracking (in-memory, resets on app restart)
# ---------------------------------------------------------------------------

_daily_counts: dict[str, int] = {}  # key: "YYYY-MM-DD"
FREE_TIER_DAILY_LIMIT = 450  # conservative buffer under 500 RPD


def _increment_daily_counter() -> int:
    """Increment today's call count and return the new value."""
    today = date.today().isoformat()
    _daily_counts[today] = _daily_counts.get(today, 0) + 1
    return _daily_counts[today]


def get_daily_usage() -> dict:
    """Return today's API usage summary.

    Example return value::

        {"date": "2026-07-24", "used": 42, "limit": 450, "remaining": 408}
    """
    today = date.today().isoformat()
    used = _daily_counts.get(today, 0)
    return {
        "date": today,
        "used": used,
        "limit": FREE_TIER_DAILY_LIMIT,
        "remaining": max(FREE_TIER_DAILY_LIMIT - used, 0),
    }


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def log_ai_call(
    *,
    provider: str,
    module: str,
    prompt_len: int,
    response_len: int,
    latency_ms: int,
    success: bool,
) -> None:
    """Log one AI API call and update the daily quota counter."""
    daily_count = _increment_daily_counter()
    remaining = FREE_TIER_DAILY_LIMIT - daily_count

    if remaining <= 50:
        logger.warning(
            "FREE-TIER ALERT: Only %d API calls remaining today!", remaining
        )

    logger.info(
        "ai_call | provider=%s module=%s prompt_chars=%d response_chars=%d "
        "latency_ms=%d success=%s daily_count=%d",
        provider,
        module,
        prompt_len,
        response_len,
        latency_ms,
        success,
        daily_count,
    )
