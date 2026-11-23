from datetime import datetime, timedelta, timezone

from app.models.log_event import LogEvent
from app.services.detection.engine import run_detection


def _make_event(db, **kwargs):
    defaults = dict(
        timestamp=datetime.now(timezone.utc),
        source="test",
        source_type="AUTH_LOG",
        event_type="AUTH_FAILURE",
        message="failed login",
        raw_log="raw",
    )
    defaults.update(kwargs)
    event = LogEvent(**defaults)
    db.add(event)
    db.flush()
    return event


def test_five_failed_attempts_no_brute_force_alert(db_session):
    base = datetime.now(timezone.utc)
    events = [
        _make_event(db_session, source_ip="1.1.1.1", username="root", timestamp=base + timedelta(seconds=i * 10))
        for i in range(5)
    ]
    alerts = run_detection(db_session, events)
    assert not any(a.detection_rule == "SSH_BRUTE_FORCE" for a in alerts)


def test_ten_failed_attempts_triggers_brute_force_alert(db_session):
    base = datetime.now(timezone.utc)
    events = [
        _make_event(db_session, source_ip="2.2.2.2", username="root", timestamp=base + timedelta(seconds=i * 10))
        for i in range(10)
    ]
    alerts = run_detection(db_session, events)
    brute_force = [a for a in alerts if a.detection_rule == "SSH_BRUTE_FORCE"]
    assert len(brute_force) == 1
    assert brute_force[0].severity == "HIGH"
    assert brute_force[0].source_ip == "2.2.2.2"
    assert len(brute_force[0].evidence) > 0


def test_failed_attempts_then_success_elevates_severity(db_session):
    base = datetime.now(timezone.utc)
    failures = [
        _make_event(db_session, source_ip="3.3.3.3", username="admin", timestamp=base + timedelta(seconds=i * 5))
        for i in range(5)
    ]
    success = _make_event(
        db_session,
        source_ip="3.3.3.3",
        username="admin",
        event_type="AUTH_SUCCESS",
        status="success",
        timestamp=base + timedelta(seconds=60),
    )
    alerts = run_detection(db_session, failures + [success])
    elevated = [a for a in alerts if a.detection_rule == "FAILED_THEN_SUCCESS"]
    assert len(elevated) == 1
    assert elevated[0].severity in ("HIGH", "CRITICAL")


def test_normal_single_login_no_alert(db_session):
    event = _make_event(
        db_session,
        source_ip="4.4.4.4",
        username="bob",
        event_type="AUTH_SUCCESS",
        status="success",
    )
    alerts = run_detection(db_session, [event])
    assert alerts == []


def test_sql_injection_detected(db_session):
    event = _make_event(
        db_session,
        source_type="APACHE_ACCESS",
        event_type="HTTP_REQUEST",
        source_ip="5.5.5.5",
        message="GET /product.php?id=1' OR '1'='1' -- -> 200",
        raw_log="raw sqli",
    )
    alerts = run_detection(db_session, [event])
    assert any(a.detection_rule == "SQL_INJECTION" for a in alerts)


def test_xss_detected(db_session):
    event = _make_event(
        db_session,
        source_type="APACHE_ACCESS",
        event_type="HTTP_REQUEST",
        source_ip="6.6.6.6",
        message="GET /comment?text=<script>alert(document.cookie)</script> -> 200",
        raw_log="raw xss",
    )
    alerts = run_detection(db_session, [event])
    assert any(a.detection_rule == "XSS" for a in alerts)


def test_path_traversal_detected(db_session):
    event = _make_event(
        db_session,
        source_type="APACHE_ACCESS",
        event_type="HTTP_REQUEST",
        source_ip="7.7.7.7",
        message="GET /download?file=../../../../etc/passwd -> 200",
        raw_log="raw traversal",
    )
    alerts = run_detection(db_session, [event])
    assert any(a.detection_rule == "PATH_TRAVERSAL" for a in alerts)


def test_sensitive_file_access_detected(db_session):
    event = _make_event(
        db_session,
        source_type="APACHE_ACCESS",
        event_type="HTTP_REQUEST",
        source_ip="8.8.8.8",
        message="GET /etc/passwd -> 200",
        raw_log="raw sensitive",
        status="200",
    )
    alerts = run_detection(db_session, [event])
    assert any(a.detection_rule == "SENSITIVE_FILE_ACCESS" for a in alerts)


def test_windows_logon_failures_trigger_brute_force_and_failed_then_success(db_session):
    """Windows Security export -> same brute-force rules as auth.log."""
    from pathlib import Path

    from app.services.ingestion.log_ingestion import ingest_raw_log

    sample = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "windows_security_events.json"
    result = ingest_raw_log(db_session, content=sample.read_text(), filename="windows_security_events.json")
    assert result.source_type == "WINDOWS_EVENT"
    assert result.events_created == 15

    from app.models.alert import Alert

    alerts = db_session.query(Alert).all()
    rules = {a.detection_rule: a for a in alerts}
    assert "SSH_BRUTE_FORCE" in rules and "FAILED_THEN_SUCCESS" in rules
    assert rules["SSH_BRUTE_FORCE"].title.startswith("Windows logon Brute Force")
    assert rules["SSH_BRUTE_FORCE"].source_ip == "198.51.100.77"
    assert rules["FAILED_THEN_SUCCESS"].severity == "CRITICAL"  # 12 failures >= threshold of 10
    assert rules["FAILED_THEN_SUCCESS"].username == "Administrator"
    assert all(a.incident_id for a in alerts)
