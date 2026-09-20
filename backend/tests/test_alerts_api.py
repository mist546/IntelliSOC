from pathlib import Path

SAMPLE_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "auth_brute_force.log"


def test_alerts_can_be_filtered_by_source_ip(client, auth_headers):
    content = SAMPLE_LOG.read_text()
    client.post("/api/logs/upload", headers=auth_headers, files={"file": ("auth_brute_force.log", content, "text/plain")})

    matching = client.get("/api/alerts", headers=auth_headers, params={"source_ip": "203.0.113.55"})
    assert matching.status_code == 200
    assert len(matching.json()) >= 1
    assert all(a["source_ip"] == "203.0.113.55" for a in matching.json())

    non_matching = client.get("/api/alerts", headers=auth_headers, params={"source_ip": "9.9.9.9"})
    assert non_matching.status_code == 200
    assert non_matching.json() == []
