import pytest

from app.services.llm.base import LLMUnavailableError
from app.services.llm import service as llm_service


class _FakeProvider:
    def __init__(self, response=None, raise_error: LLMUnavailableError | None = None):
        self._response = response
        self._raise_error = raise_error

    def generate(self, prompt, system="", json_mode=True):
        if self._raise_error:
            raise self._raise_error
        return self._response

    def is_available(self):
        return self._raise_error is None


def test_valid_json_produces_analysis(monkeypatch):
    valid_json = (
        '{"attack_type": "SSH Brute Force", "severity": "HIGH", "confidence": 0.9, '
        '"summary": "test", "evidence": ["e1"], "recommended_actions": ["a1"]}'
    )
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response=valid_json))

    analysis, error = llm_service.generate_structured_analysis("some evidence")
    assert error is None
    assert analysis.attack_type == "SSH Brute Force"
    assert analysis.severity == "HIGH"
    assert analysis.requires_human_approval is True


def test_json_wrapped_in_extra_text_is_extracted(monkeypatch):
    wrapped = 'Sure, here is the analysis:\n{"attack_type": "XSS", "severity": "MEDIUM", "confidence": 0.5, "summary": "s"}\nHope this helps!'
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response=wrapped))

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert error is None
    assert analysis.attack_type == "XSS"


def test_think_block_is_stripped_before_parsing(monkeypatch):
    with_think = '<think>let me reason about this...</think>\n{"attack_type": "Recon", "severity": "LOW", "confidence": 0.3, "summary": "s"}'
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response=with_think))

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert error is None
    assert analysis.attack_type == "Recon"


def test_malformed_json_returns_structured_failure(monkeypatch):
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response="this is not json at all"))

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert analysis is None
    assert error is not None
    assert "attempt" in error.lower() or "malformed" in error.lower()


def test_ollama_unavailable_returns_error_not_exception(monkeypatch):
    monkeypatch.setattr(
        llm_service, "_get_provider", lambda: _FakeProvider(raise_error=LLMUnavailableError("connection refused"))
    )

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert analysis is None
    assert "connection refused" in error


def test_timeout_returns_error_not_exception(monkeypatch):
    monkeypatch.setattr(
        llm_service, "_get_provider", lambda: _FakeProvider(raise_error=LLMUnavailableError("timed out after 240s"))
    )

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert analysis is None
    assert "timed out" in error


def test_missing_model_returns_error_not_exception(monkeypatch):
    monkeypatch.setattr(
        llm_service, "_get_provider", lambda: _FakeProvider(raise_error=LLMUnavailableError("Model 'x' not found"))
    )

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert analysis is None
    assert "not found" in error


def test_low_quality_output_missing_required_field_fails_validation(monkeypatch):
    # Missing required "summary" field
    incomplete = '{"attack_type": "Unknown", "severity": "LOW", "confidence": 0.1}'
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response=incomplete))

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert analysis is None
    assert error is not None


def test_invalid_severity_value_normalizes_to_unknown(monkeypatch):
    payload = '{"attack_type": "X", "severity": "SUPER_BAD", "confidence": 0.5, "summary": "s"}'
    monkeypatch.setattr(llm_service, "_get_provider", lambda: _FakeProvider(response=payload))

    analysis, error = llm_service.generate_structured_analysis("evidence")
    assert error is None
    assert analysis.severity == "UNKNOWN"
