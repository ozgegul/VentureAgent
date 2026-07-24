"""Intelligent Intent Router for Phase 2.

Classifies user messages in the chat into specific modules (swot, roadmap, etc.)
using a two-tier approach:
1. Fast keyword matching.
2. Lightweight LLM call if keywords don't trigger.
"""

from __future__ import annotations

import dataclasses
import json

from backend.services.ai_client import ask_ai, safe_parse_json
from backend.services.prompts import get_prompt, get_prompt_schema

INTENT_KEYWORDS = {
    "swot": ["swot", "güçlü yön", "zayıf yön", "fırsat", "tehdit"],
    "competitors": ["rakip", "rekabet", "competitor", "pazar oyuncuları"],
    "revenue": ["gelir modeli", "fiyatlandırma", "monetizasyon", "revenue"],
    "roadmap": ["roadmap", "yol haritası", "mvp planı", "timeline"],
    "kanban": ["kanban", "görev listesi", "yapılacaklar", "task board"],
    "investors": ["yatırımcı", "vc", "melek yatırımcı", "fonlama", "seed"],
    "pitch": ["pitch", "asansör konuşması", "elevator", "sunum", "deck"],
    "idea": ["fikir analizi", "fikir değerlendir", "venture score"],
}


@dataclasses.dataclass
class IntentResult:
    intent: str
    confidence: float
    extracted_idea: str
    suggestion_text: str


def _check_keywords(message: str) -> str | None:
    """Check if the message contains any intent keywords. Returns the intent or None."""
    msg_lower = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return intent
    return None


def classify_intent(message: str, history: list[dict]) -> IntentResult:
    """Classify the user's intent.

    Returns:
        IntentResult containing the routed intent, confidence, extracted idea,
        and suggestion text.
    """
    # Tier 1: Keyword-based fast path
    keyword_match = _check_keywords(message)
    if keyword_match:
        return IntentResult(
            intent=keyword_match,
            confidence=1.0,
            extracted_idea=message,  # We just use the message as the idea for simplicity
            suggestion_text=f"Bunun için {keyword_match.capitalize()} modülüne gitmek ister misin?",
        )

    # Tier 2: LLM-based classification
    # Convert history into a string format for the LLM prompt
    history_text = ""
    for msg in history[-5:]:  # Only take the last 5 messages for context
        history_text += f"{msg['role'].capitalize()}: {msg['content']}\n"
    
    user_prompt = f"Konuşma Geçmişi:\n{history_text}\nSon Kullanıcı Mesajı: {message}"
    
    try:
        # A lightweight LLM call (low max_tokens, high temperature=0 is done via task_complexity='low' which maps to thinking=0, and we use standard settings)
        raw_response = ask_ai(
            user_prompt=user_prompt,
            system_prompt=get_prompt("intent_classification"),
            max_tokens=200,
            json_mode=True,
            module="chat", # log as chat module
            task_complexity="low", # This maps to thinkingBudget: 0 which keeps it fast/cheap
            response_schema=get_prompt_schema("intent_classification"),
        )
        
        result_dict = safe_parse_json(raw_response)
        
        return IntentResult(
            intent=result_dict.get("intent", "chat"),
            confidence=float(result_dict.get("confidence", 0.0)),
            extracted_idea=result_dict.get("extracted_idea", message),
            suggestion_text=result_dict.get("suggestion_text", ""),
        )
        
    except Exception as e:
        # Fallback to chat intent on any error to not break the user experience
        print(f"Intent classification failed: {e}")
        return IntentResult(
            intent="chat",
            confidence=0.0,
            extracted_idea=message,
            suggestion_text=""
        )
