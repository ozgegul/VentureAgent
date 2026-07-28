import pytest
from backend.services.prompts import PROMPTS, BASE_PERSONA, get_prompt

def test_base_persona_inclusion():
    for module, prompt_data in PROMPTS.items():
        system_text = prompt_data.get("system", "")
        assert BASE_PERSONA in system_text, f"BASE_PERSONA missing in {module} prompt"

def test_prompt_non_empty():
    for module, prompt_data in PROMPTS.items():
        system_text = prompt_data.get("system", "")
        assert len(system_text.strip()) > 0, f"Prompt for {module} is empty"

def test_json_schema_definition():
    json_modules = ["swot", "competitors", "revenue", "roadmap", "kanban", "pitch_deck"]
    for module in json_modules:
        assert module in PROMPTS
        prompt_data = PROMPTS[module]
        assert "schema" in prompt_data, f"Schema definition missing in {module} prompt"
        assert isinstance(prompt_data["schema"], dict), f"Schema for {module} must be a dict"

def test_get_prompt():
    prompt = get_prompt("chat")
    assert BASE_PERSONA in prompt
    assert "Ek Görevlerin:" in prompt

    # Fallback behavior
    fallback_prompt = get_prompt("unknown_module")
    assert fallback_prompt == BASE_PERSONA
