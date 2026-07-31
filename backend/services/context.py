"""Cross-module context pipeline for VentureAgent.

Phase 3: Enables modules to share the user's active idea and prior analysis
results so that downstream modules (SWOT, roadmap, pitch, etc.) can produce
richer, more contextual output without asking the user to re-enter information.

Context is stored in the Flask **session** (cookie-based).  This means it
persists across page navigations within the same browser session but is lost
when the user closes the browser.

Public API
----------
- ``set_active_idea``   — store the user's active idea in the session
- ``get_active_idea``   — retrieve the active idea context (or ``None``)
- ``append_analysis``   — store a module's analysis result for downstream use
- ``build_enriched_prompt`` — inject prior analysis context into a prompt
"""

from __future__ import annotations

import json

from flask import session


# ---------------------------------------------------------------------------
# Context setters / getters
# ---------------------------------------------------------------------------


def set_active_idea(idea: str, sector: str = "", problem: str = "") -> None:
    """Store the user's active idea in the session for cross-module use.

    Calling this resets any previously stored analyses so that new modules
    start fresh against the updated idea.
    """
    session["active_idea"] = {
        "idea": idea,
        "sector": sector,
        "problem": problem,
        "analyses": {},  # keyed by module name
    }


def get_active_idea() -> dict | None:
    """Retrieve the active idea context, or ``None`` if not set."""
    return session.get("active_idea")


def append_analysis(module: str, result: dict | str) -> None:
    """Store a module's analysis result for downstream use.

    Parameters
    ----------
    module:
        The module name (e.g. ``"idea"``, ``"swot"``).
    result:
        The analysis result — either a parsed dict (for JSON modules) or
        a plain string (for free-text modules like ``idea`` and ``investors``).
    """
    ctx = session.get("active_idea")
    if ctx is None:
        return  # No active idea set — nothing to append to

    ctx.setdefault("analyses", {})[module] = result
    session["active_idea"] = ctx  # re-assign to mark session as modified


# ---------------------------------------------------------------------------
# Prompt enrichment
# ---------------------------------------------------------------------------


def build_enriched_prompt(module: str, base_prompt: str) -> str:
    """Inject prior analysis context into a module's system prompt.

    If there is no active idea or no prior analyses, *base_prompt* is
    returned unchanged — this keeps the function safe to call unconditionally.

    Parameters
    ----------
    module:
        The calling module's name (unused in the current implementation but
        available for future per-module enrichment strategies).
    base_prompt:
        The module's original system prompt.
    """
    ctx = get_active_idea()
    if not ctx:
        return base_prompt

    enrichment_parts: list[str] = []

    enrichment_parts.append(f"\nKullanıcının aktif fikri: {ctx['idea']}")

    if ctx.get("sector"):
        enrichment_parts.append(f"Sektör: {ctx['sector']}")

    if ctx.get("problem"):
        enrichment_parts.append(f"Çözülen problem: {ctx['problem']}")

    analyses = ctx.get("analyses", {})

    if "idea" in analyses:
        idea_result = analyses["idea"]
        if isinstance(idea_result, dict):
            score = idea_result.get("venture_score")
            if score is not None:
                enrichment_parts.append(
                    f"Önceki fikir analizi venture score: {score}"
                )
        elif isinstance(idea_result, str):
            # Truncate long free-text analysis to keep prompt manageable
            summary = idea_result[:500]
            if len(idea_result) > 500:
                summary += "…"
            enrichment_parts.append(f"Önceki fikir analizi özeti: {summary}")

    if "swot" in analyses:
        swot = analyses["swot"]
        enrichment_parts.append(
            f"Önceki SWOT analizi: {json.dumps(swot, ensure_ascii=False)}"
        )

    if "competitors" in analyses:
        comp = analyses["competitors"]
        enrichment_parts.append(
            f"Önceki rakip analizi: {json.dumps(comp, ensure_ascii=False)}"
        )

    if "revenue" in analyses:
        rev = analyses["revenue"]
        enrichment_parts.append(
            f"Önceki gelir modeli analizi: {json.dumps(rev, ensure_ascii=False)}"
        )

    if not enrichment_parts:
        return base_prompt

    enrichment = "\n".join(enrichment_parts)
    return base_prompt + "\n" + enrichment
