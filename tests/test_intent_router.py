import pytest
from backend.services.intent_router import _check_keywords, classify_intent

def test_keyword_tier_exact_matches():
    assert _check_keywords("swot analizi yapmak istiyorum") == "swot"
    assert _check_keywords("güçlü yönlerim neler") == "swot"
    assert _check_keywords("bana rakip bul") == "competitors"
    assert _check_keywords("gelir modeli nasıl olmalı") == "revenue"
    assert _check_keywords("bana bir roadmap çıkar") == "roadmap"
    assert _check_keywords("görev listesi oluştur") == "kanban"
    assert _check_keywords("melek yatırımcı arıyorum") == "investors"
    assert _check_keywords("asansör konuşması hazırla") == "pitch"
    assert _check_keywords("fikir değerlendir") == "idea"

def test_keyword_tier_no_match():
    assert _check_keywords("merhaba, nasılsın?") is None
    assert _check_keywords("uygulamamın arayüzü nasıl olmalı?") is None
    assert _check_keywords("kırmızı renk güzel mi") is None
