from pathlib import Path

SAMPLE_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "auth_brute_force.log"


def test_milestone2_agentic_investigation_end_to_end(client, auth_headers, investigate):
    """Alert -> Agent investigation -> Related evidence -> Threat intel ->
    RAG -> Ollama -> Risk assessment -> AI analysis -> Response recommendation.

    This is a real integration test against the locally running Ollama
    instance and the ingested Chroma knowledge base (not mocked), matching
    the Milestone 2 mandatory test in the project spec.
    """
    content = SAMPLE_LOG.read_text()
    upload_resp = client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", content, "text/plain")},
    )
    assert upload_resp.status_code == 200, upload_resp.text

    alerts_resp = client.get("/api/alerts", headers=auth_headers, params={"severity": "HIGH"})
    brute_force_alerts = [a for a in alerts_resp.json() if a["detection_rule"] == "SSH_BRUTE_FORCE"]
    assert len(brute_force_alerts) == 1
    alert_id = brute_force_alerts[0]["id"]

    investigation = investigate(alert_id)

    assert investigation["status"] == "COMPLETED"
    assert len(investigation["trace"]) >= 5
    assert investigation["evidence"]["alert"]["id"] == alert_id
    assert len(investigation["evidence"]["related_events"]) > 0

    assert len(investigation["threat_intelligence"]) >= 1
    assert investigation["threat_intelligence"][0]["indicator"] == "203.0.113.55"
    assert investigation["threat_intelligence"][0]["reputation"] == "malicious"

    assert investigation["risk_score"] is not None
    assert investigation["risk_score"] > 0
    assert len(investigation["risk_factors"]) > 0

    assert len(investigation["rag_sources"]) > 0

    if investigation["llm_available"]:
        analysis = investigation["ai_analysis"]
        assert analysis is not None
        assert analysis["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")
        assert 0.0 <= analysis["confidence"] <= 1.0
        assert isinstance(analysis["recommended_actions"], list)
        assert analysis["requires_human_approval"] is True
    else:
        assert investigation["error_message"]

    trace_resp = client.get(f"/api/investigations/{investigation['id']}/trace", headers=auth_headers)
    assert trace_resp.status_code == 200
    assert trace_resp.json()["status"] == "COMPLETED"

    alert_after = client.get(f"/api/alerts/{alert_id}", headers=auth_headers).json()
    assert alert_after["status"] == "INVESTIGATING"
