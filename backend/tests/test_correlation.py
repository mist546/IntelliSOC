from datetime import datetime, timezone

from app.models.alert import Alert
from app.services.correlation.correlator import correlate_alerts


def _make_alert(db, **kwargs):
    defaults = dict(
        title="test alert",
        severity="HIGH",
        confidence=0.9,
        timestamp=datetime.now(timezone.utc),
        detection_rule="SSH_BRUTE_FORCE",
        description="desc",
        evidence=["e1"],
    )
    defaults.update(kwargs)
    alert = Alert(**defaults)
    db.add(alert)
    db.flush()
    return alert


def test_related_alerts_same_ip_become_one_incident(db_session):
    a1 = _make_alert(db_session, source_ip="9.9.9.9")
    a2 = _make_alert(db_session, source_ip="9.9.9.9", detection_rule="FAILED_THEN_SUCCESS")

    incidents = correlate_alerts(db_session, [a1, a2])
    assert len(incidents) == 1
    assert a1.incident_id == a2.incident_id


def test_unrelated_alerts_become_separate_incidents(db_session):
    a1 = _make_alert(db_session, source_ip="10.10.10.10")
    a2 = _make_alert(db_session, source_ip="20.20.20.20", username="someoneelse")

    incidents = correlate_alerts(db_session, [a1, a2])
    assert len(incidents) == 2
    assert a1.incident_id != a2.incident_id
