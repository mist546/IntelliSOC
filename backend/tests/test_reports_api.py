from pathlib import Path

SAMPLE_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "auth_brute_force.log"


def _make_incident(client, auth_headers) -> str:
    content = SAMPLE_LOG.read_text()
    client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", content, "text/plain")},
    )
    incidents = client.get("/api/incidents", headers=auth_headers).json()
    assert incidents
    return incidents[0]["id"]


def test_json_report_can_be_generated_listed_and_downloaded(client, auth_headers):
    incident_id = _make_incident(client, auth_headers)

    create_resp = client.post(f"/api/reports/{incident_id}", headers=auth_headers, json={"format": "json"})
    assert create_resp.status_code == 200, create_resp.text
    report = create_resp.json()
    assert report["format"] == "json"
    assert report["incident_id"] == incident_id

    list_resp = client.get("/api/reports", headers=auth_headers, params={"incident_id": incident_id})
    assert list_resp.status_code == 200
    assert any(r["id"] == report["id"] for r in list_resp.json())

    download_resp = client.get(f"/api/reports/{report['id']}/download", headers=auth_headers)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"].startswith("application/json")
    assert "attachment" in download_resp.headers["content-disposition"]
    assert download_resp.json() == report["content"]


def test_pdf_report_can_be_generated_and_downloaded(client, auth_headers):
    incident_id = _make_incident(client, auth_headers)

    create_resp = client.post(f"/api/reports/{incident_id}", headers=auth_headers, json={"format": "pdf"})
    assert create_resp.status_code == 200, create_resp.text
    report = create_resp.json()
    assert report["format"] == "pdf"
    assert report["file_path"]

    download_resp = client.get(f"/api/reports/{report['id']}/download", headers=auth_headers)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content.startswith(b"%PDF")


def test_download_requires_auth(client, auth_headers):
    incident_id = _make_incident(client, auth_headers)
    report = client.post(f"/api/reports/{incident_id}", headers=auth_headers, json={"format": "json"}).json()

    resp = client.get(f"/api/reports/{report['id']}/download")
    assert resp.status_code == 401


def test_download_unknown_report_is_404(client, auth_headers):
    resp = client.get("/api/reports/does-not-exist/download", headers=auth_headers)
    assert resp.status_code == 404
