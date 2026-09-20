from datetime import datetime, timezone

from app.agents import investigator as investigator_module
from app.models.alert import Alert
from app.schemas.llm_output import LLMAnalysis


def _make_alert(db, **kwargs):
    defaults = dict(
        title="SSH Brute Force from 9.9.9.9",
        severity="HIGH",
        confidence=0.9,
        timestamp=datetime.now(timezone.utc),
        detection_rule="SSH_BRUTE_FORCE",
        description="desc",
        evidence=["11 failed attempts"],
        source_ip="9.9.9.9",
    )
    defaults.update(kwargs)
    alert = Alert(**defaults)
    db.add(alert)
    db.flush()
    return alert


def test_investigation_gathers_evidence_and_calls_relevant_tools(db_session, monkeypatch):
    alert = _make_alert(db_session)

    fake_analysis = LLMAnalysis(
        attack_type="SSH Brute Force", severity="HIGH", confidence=0.9, summary="test summary",
        evidence=["e1"], recommended_actions=["block ip"],
    )
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(investigator_module, "generate_structured_analysis", lambda prompt: (fake_analysis, None))

    investigation = investigator_module.investigate_alert(db_session, alert)

    assert investigation.status == "COMPLETED"
    assert investigation.llm_available is True
    assert investigation.ai_analysis["attack_type"] == "SSH Brute Force"
    # Source IP was present, so the threat-intel tool must have been called.
    assert len(investigation.threat_intelligence) >= 1
    assert investigation.threat_intelligence[0]["indicator"] == "9.9.9.9"
    # Risk engine must always run.
    assert investigation.risk_score is not None
    assert len(investigation.risk_factors) > 0
    # Trace must be a human-readable auditable list, not raw chain-of-thought.
    actions = [s["action"] for s in investigation.trace]
    assert "Alert received" in actions
    assert "Investigation completed" in actions
    assert "Risk calculated" in actions


def test_investigation_skips_threat_intel_tool_without_indicators(db_session, monkeypatch):
    alert = _make_alert(db_session, source_ip=None, username=None, title="Generic finding")
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: False)

    investigation = investigator_module.investigate_alert(db_session, alert)

    # No source_ip/username means the agent must NOT blindly call the
    # threat-intel tool (it has nothing to look up).
    assert investigation.threat_intelligence == []


def test_investigation_completes_when_llm_unavailable(db_session, monkeypatch):
    alert = _make_alert(db_session)
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: False)

    investigation = investigator_module.investigate_alert(db_session, alert)

    assert investigation.status == "COMPLETED"
    assert investigation.llm_available is False
    assert investigation.ai_analysis is None
    assert investigation.error_message is not None
    # Non-LLM evidence must still be gathered so the investigation remains useful.
    assert investigation.risk_score is not None
    assert len(investigation.threat_intelligence) >= 1


def test_investigation_surfaces_insufficient_evidence_from_llm(db_session, monkeypatch):
    alert = _make_alert(db_session, severity="LOW", confidence=0.3, evidence=[])

    fake_analysis = LLMAnalysis(
        attack_type="Unknown", severity="LOW", confidence=0.2,
        summary="Insufficient evidence to determine malicious activity with confidence.",
        insufficient_evidence=True, requires_human_approval=True,
    )
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(investigator_module, "generate_structured_analysis", lambda prompt: (fake_analysis, None))

    investigation = investigator_module.investigate_alert(db_session, alert)

    assert investigation.ai_analysis["insufficient_evidence"] is True
    assert investigation.ai_analysis["requires_human_approval"] is True
