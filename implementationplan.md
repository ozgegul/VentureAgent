Agent Response Quality and Routing Improvement
A step-by-step technical roadmap for enhancing VentureAgent's AI response quality and inter-module routing, based on a comprehensive analysis of the current codebase.
Current Architecture Summary
VentureAgent is a Flask-based application with 12 route blueprints and a single provider-agnostic AI client (ai_client.py). Each module (SWOT, Competitors, Revenue, etc.) is a self-contained blueprint with its own hardcoded SYSTEM_PROMPT and direct calls to ask_ai() / ask_ai_conversation(). The free-form chat.py module is the only multi-turn conversation endpoint.
Identified Weak Points
WP-1: Scattered, Inconsistent Prompt Templates
10 different SYSTEM_PROMPT strings are hardcoded across 8 route files (chat, idea, swot, competitors, revenue, roadmap, kanban, investors, and 2 in pitch).
Prompts vary wildly in instruction depth. Some specify strict JSON schemas (swot.py L11-21), others are bare one-liners (idea.py L15-16).
No shared base persona, formatting conventions, or quality guardrails are enforced across prompts.
Prompt changes require editing each route file individually — high risk of drift.
WP-2: No Intelligent Routing from Chat to Modules
The chat system prompt (chat.py L19-33) says "yönlendirmek" (redirect to modules) but only in natural language. There is no programmatic intent detection or auto-routing.
A user saying "Fikrimin SWOT'unu çıkar" in chat gets a free-text response instead of being routed to the structured SWOT module that would produce a proper JSON grid.
Module selection is 100% manual (user must click the navbar link).
WP-3: Zero Cross-Module Context Sharing
Each module operates in complete isolation. If a user analyzes an idea in the Idea module, then navigates to SWOT, they must re-enter the idea from scratch.
The chat session history (chat.py L50-63) is stored in Flask session cookies but is never passed to other modules.
VentureScore results from market_scoring.py are saved to the DB but never referenced by downstream modules (SWOT, roadmap, pitch, etc.).
WP-4: AI Client Fragility & Missing Guardrails
No retry logic: a single transient 429/503 from Gemini or Claude kills the request (ai_client.py L163-168).
40-second hard timeout with no user-facing feedback about progress.
safe_parse_json() (L59-62) only strips markdown fences. If the LLM returns malformed JSON (missing key, extra comma), the whole module crashes with an opaque error.
No response validation: a SWOT response missing the threats key would pass safe_parse_json but silently break the template.
Gemini conversation support is a simple concatenation hack (L184-191) — multi-turn loses role boundaries.
thinkingBudget: 0 in Gemini config (L141-143) disables reasoning for all calls, including complex analysis tasks.
WP-5: No Response Quality Measurement
No logging of prompts, responses, latency, or token usage.
No way to A/B test prompt changes or measure regression.
Broad except Exception blocks (idea.py L77, swot.py L47, etc.) swallow all errors — hard to debug production issues.
Proposed Changes
Phase 1 — Centralized Prompt Registry (Foundation)
Goal: Single source of truth for all prompts, shared base persona, versioned and testable.
[NEW] prompts.py
Create a dedicated prompt registry module:
python

# Centralized prompt definitions
BASE_PERSONA = """Sen VentureAgent'sın — girişimcilerin fikir ortağı gibi 
davranan uzman bir yapay zeka danışmanısın. Her cevabında:
- Somut, uygulanabilir ve veri destekli öneriler ver
- Genel geçer motivasyon cümleleri kullanma
- Emin olmadığın verilerin tahmini olduğunu belirt
- Türkçe konuş
"""

QUALITY_GUARDRAILS = """
Cevap kalitesi kuralları:
- Her madde en az bir somut örnek veya aksiyon içersin
- Sektöre/fikre özgü ol, şablon cümlelerden kaçın
- JSON isteniyorsa SADECE geçerli JSON döndür, başka açıklama ekleme
"""

# Per-module prompts that compose BASE_PERSONA + specific instructions
PROMPTS = {
    "chat": { "system": BASE_PERSONA + "..." , "version": "1.0" },
    "swot": { "system": BASE_PERSONA + QUALITY_GUARDRAILS + "...", "schema": {...}, "version": "1.0" },
    # ... etc for each module
}
Key design decisions:
Each prompt composes BASE_PERSONA + QUALITY_GUARDRAILS + module-specific instructions
Prompts include a version field for tracking changes
JSON schema modules include the expected schema as a Python dict for runtime validation
All 10 existing hardcoded prompts move here
[MODIFY] All route files (swot.py, competitors.py, revenue.py, roadmap.py, kanban.py, investors.py, pitch.py, idea.py, chat.py)
Replace hardcoded SYSTEM_PROMPT constants with imports from prompts.py:
python

# Before
SYSTEM_PROMPT = """Sen deneyimli bir startup stratejistisin..."""

# After  
from backend.services.prompts import get_prompt
SYSTEM_PROMPT = get_prompt("swot")
Phase 2 — Intelligent Intent Router (Core Feature)
Goal: When a user types in the chat, classify their intent and either answer directly or route to the appropriate structured module.
[NEW] intent_router.py
Two-tier intent classification:
Tier 1 — Keyword-based fast path (no LLM call needed):
python

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
Tier 2 — LLM-based classification (when keywords don't match):
python

def classify_intent(message: str, history: list[dict]) -> IntentResult:
    """
    Returns:
        IntentResult with:
        - intent: "chat" | "swot" | "competitors" | ... 
        - confidence: 0.0-1.0
        - extracted_idea: str (the idea text pulled from conversation)
        - suggestion_text: str (human-readable suggestion for the user)
    """
A lightweight LLM call (low max_tokens, high temperature=0) classifies intent into one of the module categories. Crucially, this does NOT auto-redirect — it returns a suggestion that the chat module can surface as an actionable card.
[MODIFY] chat.py
Enhance the /message endpoint:
python

@chat_bp.route("/message", methods=["POST"])
def send_message():
    # ... existing message handling ...
    
    # After getting the AI reply, check for routing opportunity
    intent = classify_intent(user_message, history)
    
    response = {"reply": reply}
    if intent.intent != "chat" and intent.confidence > 0.7:
        response["suggestion"] = {
            "module": intent.intent,
            "url": url_for(f"{intent.intent}.{intent.intent}_form"),
            "text": intent.suggestion_text,
            "prefill_idea": intent.extracted_idea,
        }
    
    return jsonify(response)
[MODIFY] chat.js
Render routing suggestions as clickable cards below the assistant's reply:
javascript

if (data.suggestion) {
    const card = document.createElement("div");
    card.className = "routing-suggestion-card";
    card.innerHTML = `
        <p>${data.suggestion.text}</p>
        <a href="${data.suggestion.url}?idea=${encodeURIComponent(data.suggestion.prefill_idea)}">
            Modüle git →
        </a>`;
    messagesEl.appendChild(card);
}
Phase 3 — Cross-Module Context Pipeline (Quality Multiplier)
Goal: Previous analyses enrich subsequent module calls automatically.
[NEW] context.py
Session-based context manager:
python

def set_active_idea(idea: str, sector: str = "", problem: str = "") -> None:
    """Store the user's active idea in session for cross-module use."""
    session["active_idea"] = {
        "idea": idea, "sector": sector, "problem": problem,
        "analyses": {}  # keyed by module name
    }

def get_active_idea() -> dict | None:
    """Retrieve the active idea context."""
    return session.get("active_idea")

def append_analysis(module: str, result: dict) -> None:
    """Store a module's analysis result for downstream use."""
    ctx = session.get("active_idea", {})
    ctx.setdefault("analyses", {})[module] = result
    session["active_idea"] = ctx

def build_enriched_prompt(module: str, base_prompt: str) -> str:
    """Inject prior analysis context into a module's prompt."""
    ctx = get_active_idea()
    if not ctx:
        return base_prompt
    
    enrichment = f"\nKullanıcının aktif fikri: {ctx['idea']}"
    if "idea" in ctx.get("analyses", {}):
        enrichment += f"\nÖnceki fikir analizi venture score: {ctx['analyses']['idea'].get('venture_score')}"
    if "swot" in ctx.get("analyses", {}):
        enrichment += f"\nÖnceki SWOT analizi: {json.dumps(ctx['analyses']['swot'], ensure_ascii=False)}"
    # ... etc.
    
    return base_prompt + enrichment
[MODIFY] Route files: idea.py, swot.py, competitors.py, revenue.py, roadmap.py, pitch.py
Two changes per route:
On GET: Pre-fill form fields from get_active_idea() so the user doesn't re-type
On POST: Call append_analysis(module, result) after successful AI analysis, and use build_enriched_prompt() to inject prior context into the prompt
[MODIFY] HTML templates (swot.html, competitors.html, revenue.html, etc.)
Add value="{{ active_idea }}" to idea input fields for auto-fill.
Phase 4 — AI Client Hardening (Reliability)
Goal: Make LLM calls robust, observable, and self-healing.
[MODIFY] ai_client.py
4a. Retry with exponential backoff:
python

import time

def _retry(fn, max_retries=3, base_delay=1.0):
    """Retry with exponential backoff for transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (urllib.error.HTTPError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            if hasattr(e, 'code') and e.code not in (429, 500, 502, 503):
                raise  # Don't retry client errors
            time.sleep(base_delay * (2 ** attempt))
4b. Structured JSON validation:
python

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
4c. Dynamic thinkingBudget per task complexity:
python

def _build_gemini_config(max_tokens: int, task_complexity: str = "low") -> dict:
    thinking_budgets = {"low": 0, "medium": 1024, "high": 4096}
    return {
        "temperature": 0.4,
        "maxOutputTokens": max_tokens,
        "thinkingConfig": {
            "thinkingBudget": thinking_budgets.get(task_complexity, 0),
        },
    }
4d. Proper Gemini multi-turn conversation support:
Replace the string-concatenation hack in _format_conversation_for_gemini() with proper Gemini contents array format:
python

def _ask_gemini_conversation(messages: list[dict], system_prompt: str, max_tokens: int) -> str:
    """Send proper multi-turn conversation to Gemini."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    
    payload = {
        "contents": contents,
        "generationConfig": _build_gemini_config(max_tokens, "medium"),
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    # ... send request
[NEW] ai_logger.py
Observability layer:
python

import logging
import time

logger = logging.getLogger("ventureagent.ai")

def log_ai_call(provider, module, prompt_len, response_len, latency_ms, success):
    logger.info(
        "ai_call | provider=%s module=%s prompt_chars=%d response_chars=%d "
        "latency_ms=%d success=%s",
        provider, module, prompt_len, response_len, latency_ms, success
    )
Wrap ask_ai() and ask_ai_conversation() to automatically log every call with timing, module name, and success/failure.
Phase 5 — ask_ai Signature Enhancement
Goal: Pass module context through the AI client for logging and complexity-aware configuration.
[MODIFY] ai_client.py
Extend the ask_ai() signature:
python

def ask_ai(
    user_prompt: str,
    system_prompt: str = "",
    max_tokens: int = 1500,
    json_mode: bool = False,
    module: str = "unknown",           # NEW: for logging & routing
    task_complexity: str = "low",       # NEW: controls thinkingBudget
    response_schema: dict | None = None # NEW: for validation
) -> str:
This is backwards-compatible (all new params have defaults) — existing callers continue to work unmodified.
Open Questions
IMPORTANT
Intent Router behavior: When the router detects that a chat message should go to a structured module (e.g., "Fikrimin SWOT'unu çıkar"), should we:
(A) Show a suggestion card and let the user click through (recommended — less disruptive), or
(B) Auto-redirect and run the structured analysis inline within the chat window? Option A is in the plan above, but Option B is also viable if you prefer a more "agentic" feel.
IMPORTANT
Context persistence scope: The current plan uses Flask session (cookie-based) for cross-module context. This means context is lost when the user closes the browser. Should we:
(A) Keep session-based context (simpler, matches current architecture), or
(B) Persist active idea context to SQLite (survives browser close, enables multi-device)?
NOTE
Gemini thinkingBudget: The current config disables thinking (thinkingBudget: 0) globally. The plan proposes making it dynamic per task. For Gemini 2.5 Flash, enabling thinking adds latency but significantly improves complex analysis quality (SWOT, roadmap, pitch). Is the latency tradeoff acceptable?
Verification Plan
Automated Tests
Unit tests for the prompt registry:
bash

python -m pytest tests/test_prompts.py -v
Every prompt in PROMPTS dict composes BASE_PERSONA
All prompts are non-empty and under token limits
JSON-mode prompts include valid schema definitions
Unit tests for intent classification:
bash

python -m pytest tests/test_intent_router.py -v
Keyword tier: 15+ test messages → expected intents
LLM tier: mock AI responses → correct classification
Edge cases: empty input, ambiguous messages, multi-intent messages
Unit tests for JSON validation:
bash

python -m pytest tests/test_ai_client.py -v
safe_parse_json with markdown fences, surrounding text, missing keys
Retry logic with mock HTTP errors (429, 503, timeout)
Schema validation catches missing required fields
Integration tests for context pipeline:
bash

python -m pytest tests/test_context.py -v
Set idea → navigate to SWOT → idea pre-filled
Complete idea analysis → SWOT → enriched prompt includes VentureScore
Manual Verification
Chat routing flow: Type "Bu fikir için SWOT analizi yap" in chat → verify suggestion card appears → click through to SWOT module → verify idea is pre-filled
Cross-module flow: Complete an idea analysis → navigate to Roadmap → verify idea + VentureScore context are injected into the prompt
Retry resilience: Temporarily use an invalid API key → verify retry attempts are logged and user gets a clear error message
Response quality comparison: Run the same 5 test ideas through SWOT/competitors before and after prompt improvements → compare output specificity and actionability
Prompt Regression Harness
Create a set of "golden" test cases:

tests/golden_prompts/
├── swot_input_1.json     # Input idea
├── swot_expected_1.json  # Expected JSON schema + quality checks
├── chat_intent_1.json    # Chat message + expected routing
└── ...
Run nightly to catch prompt regressions when prompts are updated.
Implementation Order & Risk Assessment
PhaseFiles ModifiedRiskEstimated EffortPhase 1: Prompt Registry1 new + 9 modified🟢 Low — purely organizational refactor2-3 hoursPhase 4: AI Client Hardening1 modified + 1 new🟢 Low — internal changes, same external API2-3 hoursPhase 5: ask_ai Signature1 modified + 9 callers🟢 Low — backwards compatible1 hourPhase 3: Context Pipeline1 new + 6 modified + templates🟡 Medium — touches session/UI3-4 hoursPhase 2: Intent Router1 new + 2 modified + JS🟡 Medium — new user-facing behavior3-4 hours
TIP
Recommended order: Phase 1 → 4 → 5 → 3 → 2. Start with zero-risk infrastructure improvements (prompts, retries), then build the user-facing features on the solid foundation. 