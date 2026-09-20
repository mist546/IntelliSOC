from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs"


def test_web_attacks_sample_triggers_expected_rules(client, auth_headers):
    content = (SAMPLE_DIR / "apache_web_attacks.log").read_text()
    resp = client.post(
        "/api/logs/upload", headers=auth_headers, files={"file": ("apache_web_attacks.log", content, "text/plain")}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["source_type"] == "APACHE_ACCESS"

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    rules_triggered = {a["detection_rule"] for a in alerts}
    assert "SQL_INJECTION" in rules_triggered
    assert "XSS" in rules_triggered
    assert "PATH_TRAVERSAL" in rules_triggered
    assert "SENSITIVE_FILE_ACCESS" in rules_triggered


def test_normal_web_traffic_triggers_no_alerts(client, auth_headers):
    content = (SAMPLE_DIR / "nginx_normal_traffic.log").read_text()
    resp = client.post(
        "/api/logs/upload", headers=auth_headers, files={"file": ("nginx_normal_traffic.log", content, "text/plain")}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["alerts_created"] == 0


def test_normal_auth_activity_triggers_no_alerts(client, auth_headers):
    content = (SAMPLE_DIR / "auth_normal.log").read_text()
    resp = client.post("/api/logs/upload", headers=auth_headers, files={"file": ("auth_normal.log", content, "text/plain")})
    assert resp.status_code == 200, resp.text
    assert resp.json()["alerts_created"] == 0
