from pathlib import Path

SAMPLE_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "auth_brute_force.log"


def test_milestone1_golden_path_auth_log_to_incident(client, auth_headers):
    """auth.log -> parser -> normalized events -> detection -> alert -> correlation -> incident"""
    content = SAMPLE_LOG.read_text()

    upload_resp = client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", content, "text/plain")},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    result = upload_resp.json()

    assert result["source_type"] == "AUTH_LOG"
    assert result["events_created"] == 18
    assert result["alerts_created"] >= 2  # SSH_BRUTE_FORCE + FAILED_THEN_SUCCESS
    assert result["incidents_created"] >= 1

    logs_resp = client.get("/api/logs", headers=auth_headers, params={"source_ip": "203.0.113.55"})
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()) == 12  # 11 failures + 1 success

    alerts_resp = client.get("/api/alerts", headers=auth_headers, params={"severity": "HIGH"})
    assert alerts_resp.status_code == 200
    high_alerts = alerts_resp.json()
    brute_force_alerts = [a for a in high_alerts if a["detection_rule"] == "SSH_BRUTE_FORCE"]
    assert len(brute_force_alerts) == 1
    assert brute_force_alerts[0]["source_ip"] == "203.0.113.55"
    assert brute_force_alerts[0]["incident_id"] is not None

    incident_id = brute_force_alerts[0]["incident_id"]
    incident_resp = client.get(f"/api/incidents/{incident_id}", headers=auth_headers)
    assert incident_resp.status_code == 200
    incident = incident_resp.json()
    assert incident["severity"] in ("HIGH", "CRITICAL")
    assert len(incident["alerts"]) >= 2

    incidents_resp = client.get("/api/incidents", headers=auth_headers)
    assert incidents_resp.status_code == 200
    assert len(incidents_resp.json()) >= 1


def test_full_golden_path_log_to_dashboard(client, auth_headers, monkeypatch, investigate):
    """Section 37 golden path, deterministic and offline:

    synthetic auth.log -> upload -> parse -> normalize -> store -> brute-force
    detection -> HIGH alert -> correlation -> incident -> Investigate with AI
    -> agent (related logs, indicator extraction, threat intel, RAG*, risk,
    AI analysis, response recommendation) -> investigation report -> dashboard.

    The LLM call is mocked so the test never depends on Ollama; the live,
    unmocked variant is tests/test_investigation_milestone2.py.
    (*RAG degrades gracefully if the embedding model is not reachable.)
    """
    from app.agents import investigator as investigator_module
    from app.schemas.llm_output import LLMAnalysis

    fake_analysis = LLMAnalysis(
        attack_type="SSH Brute Force",
        severity="HIGH",
        confidence=0.88,
        summary="Repeated failed SSH logins followed by a successful login from the same IP.",
        evidence=["11 failed attempts", "successful login afterwards"],
        mitre_technique="T1110",
        recommended_actions=["Review the successful session", "Consider blocking 203.0.113.55"],
    )
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(investigator_module, "generate_structured_analysis", lambda prompt: (fake_analysis, None))

    # 1. Upload -> parse -> normalize -> store -> detect -> correlate
    upload = client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", SAMPLE_LOG.read_text(), "text/plain")},
    ).json()
    assert upload["alerts_created"] >= 2 and upload["incidents_created"] >= 1

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    brute = next(a for a in alerts if a["detection_rule"] == "SSH_BRUTE_FORCE")
    assert brute["severity"] == "HIGH" and brute["incident_id"]
    assert len(brute["evidence"]) > 0  # never an alert without evidence

    # 2. Investigate with AI
    inv = investigate(brute["id"])
    assert inv["status"] == "COMPLETED" and inv["llm_available"] is True
    actions = [s["action"] for s in inv["trace"]]
    for expected in (
        "Alert received",
        "Related authentication/activity logs searched",
        "Indicators extracted",
        "Failed authentication attempts found",
        "Successful login detected",
        "Threat intelligence lookup completed",
        "Risk calculated",
        "Evidence sent to local LLM",
        "AI analysis validated",
        "Response recommendation generated",
        "Investigation completed",
        "Investigation report generated",
    ):
        assert expected in actions, f"missing trace step: {expected}"
    assert inv["threat_intelligence"][0]["indicator"] == "203.0.113.55"
    assert inv["threat_intelligence"][0]["reputation"] == "malicious"
    assert inv["risk_score"] > 0 and inv["risk_factors"]
    assert inv["ai_analysis"]["requires_human_approval"] is True
    assert inv["ai_analysis"]["recommended_actions"]

    # 3. Report - the agent already produced a JSON report; a PDF can be added on demand
    reports = client.get("/api/reports", headers=auth_headers, params={"incident_id": brute["incident_id"]}).json()
    assert any(r["format"] == "json" for r in reports)
    json_report = next(r for r in reports if r["format"] == "json")
    content = json_report["content"]
    assert content["investigations"][0]["risk_score"] == inv["risk_score"]
    assert content["investigations"][0]["recommended_actions"] == fake_analysis.recommended_actions
    # The report must never claim containment happened.
    assert "No containment actions were executed automatically" in content["containment_status"]
    assert content["investigations"][0]["requires_human_approval"] is True

    pdf = client.post(f"/api/reports/{brute['incident_id']}", headers=auth_headers, json={"format": "pdf"})
    assert pdf.status_code == 200
    download = client.get(f"/api/reports/{pdf.json()['id']}/download", headers=auth_headers)
    assert download.status_code == 200 and download.content[:4] == b"%PDF"

    # 4. Dashboard reflects everything
    stats = client.get("/api/dashboard/statistics", headers=auth_headers).json()
    assert stats["alert_counts_by_severity"]["HIGH"] >= 1
    assert stats["open_incidents"] >= 1
    assert stats["total_log_events"] == upload["events_created"]
    assert any(i["id"] == inv["id"] for i in stats["recent_investigations"])
    assert any(ip["source_ip"] == "203.0.113.55" for ip in stats["top_source_ips"])
