import pytest
import urllib.error
from unittest.mock import patch, MagicMock
from backend.services.ai_client import safe_parse_json, _retry

def test_safe_parse_json_basic():
    raw = '```json\n{"test": 1}\n```'
    assert safe_parse_json(raw) == {"test": 1}

def test_safe_parse_json_surrounding_text():
    raw = 'Here is the JSON:\n{"key": "value"}\nHope this helps!'
    assert safe_parse_json(raw) == {"key": "value"}

def test_safe_parse_json_schema_validation():
    schema = {"required_key": str}
    raw = '{"required_key": "val", "other": 2}'
    # Should not raise
    assert safe_parse_json(raw, schema) == {"required_key": "val", "other": 2}
    
    raw_invalid = '{"other": 2}'
    with pytest.raises(ValueError, match="AI yanıtında eksik alanlar"):
        safe_parse_json(raw_invalid, schema)

def test_retry_success_first_try():
    mock_fn = MagicMock(return_value="success")
    result = _retry(mock_fn, max_retries=3, base_delay=0.1)
    assert result == "success"
    assert mock_fn.call_count == 1

def test_retry_transient_error_then_success():
    class MockHTTPError(urllib.error.HTTPError):
        def __init__(self, code):
            self.code = code

    mock_fn = MagicMock(side_effect=[MockHTTPError(429), MockHTTPError(503), "success"])
    result = _retry(mock_fn, max_retries=3, base_delay=0.01)
    assert result == "success"
    assert mock_fn.call_count == 3

def test_retry_gives_up_after_max_retries():
    class MockHTTPError(urllib.error.HTTPError):
        def __init__(self, code):
            self.code = code

    mock_fn = MagicMock(side_effect=MockHTTPError(500))
    with pytest.raises(MockHTTPError):
        _retry(mock_fn, max_retries=3, base_delay=0.01)
    assert mock_fn.call_count == 3
