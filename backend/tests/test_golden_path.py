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
