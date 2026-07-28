from backend.services.context import set_active_idea, get_active_idea, append_analysis, build_enriched_prompt
from flask import Flask, session

def test_context_pipeline():
    app = Flask(__name__)
    app.secret_key = "test"
    
    with app.test_request_context():
        # Test 1: Set idea
        set_active_idea("A new startup", "Tech", "A problem")
        ctx = get_active_idea()
        assert ctx["idea"] == "A new startup"
        
        # Test 2: Build prompt with no analysis yet
        base = "Base Prompt"
        enriched = build_enriched_prompt("swot", base)
        assert "A new startup" in enriched
        assert "venture score" not in enriched
        
        # Test 3: Append analysis
        append_analysis("idea", {"venture_score": 85})
        enriched2 = build_enriched_prompt("roadmap", base)
        assert "venture score: 85" in enriched2
