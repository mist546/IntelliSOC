import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.agent import Agent
from app.models.log_event import LogEvent
from app.services.parsing.detector import detect_source_type
from app.services.parsing.wazuh import parse_wazuh_alert, parse_wazuh_alerts

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_logs" / "wazuh_alerts.json"
ARCHIVES = SAMPLE.with_name("wazuh_archives.json")
LAB_IP = "172.28.0.66"
SSH_IP = "198.51.100.23"
WIN_IP = "198.51.100.61"
WEB_IP = "198.51.100.88"


def _alerts() -> list[dict]:
    return [json.loads(line) for line in SAMPLE.read_text().splitlines() if line.strip()]


def _first(rule_id: str) -> dict:
    return next(a for a in _alerts() if a["rule"]["id"] == rule_id)


def _register_agent(client, auth_headers) -> dict:
    resp = client.post("/api/agents/register", headers=auth_headers, json={"name": "wazuh-bridge", "hostname": "wazuh-manager"})
    assert resp.status_code in (200, 201), resp.text
    registered = resp.json()
    return {"X-Agent-Id": registered["id"], "X-Agent-Key": registered["api_key"]}


def test_ssh_failure_with_iso_timestamp_maps_to_auth_log():
    event = parse_wazuh_alert(_first("5760"))
    assert event.source_type == "AUTH_LOG"
    assert event.event_type == "AUTH_FAILURE"
    assert event.source_ip == SSH_IP
    assert event.username == "admin"
    assert event.host == "ubuntu-web01"
    assert event.destination_ip == "192.168.56.20"
    # 14:10:00.123+05:00 -> naive UTC
    assert event.timestamp.isoformat() == "2026-11-09T09:10:00.123000"
    assert event.metadata["wazuh"]["rule_id"] == "5760"
    assert "T1110.001" in event.metadata["wazuh"]["mitre_ids"]


def test_ssh_success_maps_to_auth_success():
    event = parse_wazuh_alert(_first("5715"))
    assert (event.source_type, event.event_type, event.username) == ("AUTH_LOG", "AUTH_SUCCESS", "root")


def test_frequency_alert_carries_its_own_failure():
    # Wazuh writes the 8th failure only as the rule-5712 alert, not as 5760 too.
    event = parse_wazuh_alert(_first("5712"))
    assert (event.source_type, event.event_type, event.source_ip) == ("AUTH_LOG", "AUTH_FAILURE", SSH_IP)
    assert event.metadata["wazuh"]["rule_id"] == "5712"


def test_windows_logon_failure_maps_to_windows_event():
    event = parse_wazuh_alert(_first("60122"))
    assert event.source_type == "WINDOWS_EVENT"
    assert event.event_type == "AUTH_FAILURE"
    assert event.source_ip == WIN_IP
    assert event.username == "Administrator"
    assert event.host == "win10-lab"
    assert event.metadata["event_id"] == 4625
    assert event.metadata["logon_type"] == 3


def test_windows_local_logon_has_no_source_ip():
    alert = _first("60122")
    alert["data"]["win"]["eventdata"]["ipAddress"] = "-"
    assert parse_wazuh_alert(alert).source_ip is None


def test_web_access_alert_maps_to_apache_access():
    event = parse_wazuh_alert(_first("31103"))
    assert event.source_type == "APACHE_ACCESS"
    assert event.event_type == "HTTP_REQUEST"
    assert event.source_ip == WEB_IP
    assert event.host == "ubuntu-web01"
    assert "UNION" in event.metadata["path"]


def test_unrelated_alert_is_stored_as_wazuh_event():
    event = parse_wazuh_alert(_first("550"))
    assert (event.source_type, event.event_type) == ("WAZUH", "WAZUH_ALERT")
    assert event.message == "Integrity checksum changed."


def test_malformed_input_does_not_crash():
    assert parse_wazuh_alert({}) is None
    assert parse_wazuh_alert({"rule": "nope"}) is None
    assert parse_wazuh_alerts("") == []
    assert parse_wazuh_alerts("not json\n{also not json") == []
    event = parse_wazuh_alert({"rule": {"id": "1"}, "agent": {}, "timestamp": "garbage"})
    assert event.event_type == "WAZUH_ALERT"


def _archives() -> list[dict]:
    return [json.loads(line) for line in ARCHIVES.read_text().splitlines() if line.strip()]


def test_archive_keeps_every_log_line():
    # Real archives.json from the Docker lab's Wazuh mode: hydra made 13
    # failed SSH logins and 1 success; nginx logged 5 requests.
    events = [parse_wazuh_alert(a) for a in _archives()]
    assert all(events)
    failures = [e for e in events if e.event_type == "AUTH_FAILURE" and "Failed password" in e.message]
    assert len(failures) == 13
    assert {e.source_ip for e in failures} == {LAB_IP}
    success = [e for e in events if e.event_type == "AUTH_SUCCESS"]
    # The success only exists as rule 40112 ("success after failures").
    assert [(e.username, e.metadata["wazuh"]["rule_id"]) for e in success] == [("admin", "40112")]
    web = [e for e in events if e.source_type == "NGINX_ACCESS"]
    assert len(web) == 5 and {e.host for e in web} == {"lab-web01"}
    # Lines that matched no Wazuh rule (here a plain "GET /") are kept too.
    assert any(e.metadata["wazuh"].get("rule_id") is None for e in web)


def test_archive_line_without_rule_is_stored():
    event = parse_wazuh_alert({"agent": {"name": "vm1"}, "decoder": {"name": "unknown"}, "full_log": "hello"})
    assert (event.source_type, event.event_type, event.raw_log) == ("WAZUH", "WAZUH_EVENT", "hello")


def test_archives_upload_detects_lab_attacks(client, auth_headers):
    resp = client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("archives.json", ARCHIVES.read_text(), "application/json")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["source_type"] == "WAZUH"
    alerts = client.get("/api/alerts", headers=auth_headers, params={"limit": 100}).json()
    rules = {a["detection_rule"] for a in alerts if a["source_ip"] == LAB_IP}
    assert {"SSH_BRUTE_FORCE", "FAILED_THEN_SUCCESS", "SQL_INJECTION", "XSS", "PATH_TRAVERSAL", "SENSITIVE_FILE_ACCESS"} <= rules


def test_detector_recognises_wazuh_ndjson_and_array():
    content = SAMPLE.read_text()
    assert detect_source_type("wazuh_alerts.json", content) == "WAZUH"
    assert detect_source_type("alerts.log", content) == "WAZUH"
    assert detect_source_type("export.json", json.dumps(_alerts()[:3])) == "WAZUH"
    assert len(parse_wazuh_alerts(json.dumps(_alerts()))) == len(_alerts())


def _assert_expected_alerts(client, auth_headers):
    alerts = client.get("/api/alerts", headers=auth_headers, params={"limit": 100}).json()
    by_rule_ip = {(a["detection_rule"], a["source_ip"]): a for a in alerts}
    assert ("SSH_BRUTE_FORCE", SSH_IP) in by_rule_ip
    assert ("FAILED_THEN_SUCCESS", SSH_IP) in by_rule_ip
    assert ("SSH_BRUTE_FORCE", WIN_IP) in by_rule_ip
    assert ("FAILED_THEN_SUCCESS", WIN_IP) in by_rule_ip
    assert any(a["source_ip"] == WEB_IP and a["detection_rule"] == "SQL_INJECTION" for a in alerts)

    ssh = by_rule_ip[("SSH_BRUTE_FORCE", SSH_IP)]
    assert ssh["host"] == "ubuntu-web01"
    # 10 rule-5760 failures + the one carried by the rule-5712 alert.
    assert ssh["description"].startswith("11 failed SSH")
    assert by_rule_ip[("SSH_BRUTE_FORCE", WIN_IP)]["title"].startswith("Windows logon Brute Force")
    # Wazuh's own rule hits never become IntelliSOC alerts.
    assert not any("Integrity" in a["title"] for a in alerts)


def test_wazuh_endpoint_ingests_and_detects(client, auth_headers, db_session):
    agent_headers = _register_agent(client, auth_headers)

    resp = client.post("/api/events/wazuh", headers=agent_headers, json={"alerts": _alerts() + [{"junk": True}]})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["events_created"] == len(_alerts())
    assert body["skipped"] == 1
    assert body["alerts_created"] >= 5

    _assert_expected_alerts(client, auth_headers)

    db_session.expire_all()
    agent = db_session.query(Agent).filter(Agent.id == agent_headers["X-Agent-Id"]).one()
    assert agent.last_seen_at is not None
    stored = db_session.query(LogEvent).filter(LogEvent.event_type == "WAZUH_ALERT").one()
    assert stored.agent_id == agent.id and stored.source == "wazuh-bridge"


def test_wazuh_endpoint_rejects_bad_credentials(client, auth_headers):
    agent_headers = _register_agent(client, auth_headers)
    agent_headers["X-Agent-Key"] = "wrong"
    assert client.post("/api/events/wazuh", headers=agent_headers, json={"alerts": []}).status_code == 401
    assert client.post("/api/events/wazuh", json={"alerts": []}).status_code == 401


def test_wazuh_alerts_json_upload_produces_same_alerts(client, auth_headers):
    resp = client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("alerts.json", SAMPLE.read_text(), "application/json")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["source_type"] == "WAZUH"
    _assert_expected_alerts(client, auth_headers)


def test_logs_api_exposes_wazuh_context_and_filters(client, auth_headers):
    agent_headers = _register_agent(client, auth_headers)
    client.post("/api/events/wazuh", headers=agent_headers, json={"alerts": _alerts()})
    client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth.log", "Jan 12 10:15:23 web01 sshd[1]: Failed password for root from 192.0.2.9 port 22 ssh2\n", "text/plain")},
    )

    logs = client.get("/api/logs", headers=auth_headers, params={"limit": 500}).json()
    plain = next(log for log in logs if log["source_ip"] == "192.0.2.9")
    assert plain["metadata"] is None or "wazuh" not in plain["metadata"]

    via_wazuh = client.get("/api/logs", headers=auth_headers, params={"limit": 500, "wazuh": True}).json()
    assert len(via_wazuh) == len(_alerts())
    assert all("wazuh" in log["metadata"] for log in via_wazuh)
    ssh = next(log for log in via_wazuh if log["source_ip"] == SSH_IP and log["metadata"]["wazuh"].get("rule_id") == "5760")
    assert ssh["source_type"] == "AUTH_LOG"
    assert ssh["metadata"]["wazuh"]["agent_name"] == "ubuntu-web01"
    assert ssh["metadata"]["wazuh"]["rule_level"] is not None

    windows = client.get("/api/logs", headers=auth_headers, params={"limit": 500, "source_type": "WINDOWS_EVENT"}).json()
    assert windows and all(log["source_type"] == "WINDOWS_EVENT" for log in windows)

    single = client.get(f"/api/logs/{ssh['id']}", headers=auth_headers).json()
    assert single["metadata"]["wazuh"]["rule_id"] == "5760"
