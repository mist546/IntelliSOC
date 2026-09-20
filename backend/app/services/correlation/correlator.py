from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.incident import Incident
from app.utils.logging import get_logger

logger = get_logger(__name__)

CORRELATION_WINDOW_MINUTES = 30
SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _find_related_incident(db: Session, alert: Alert) -> Incident | None:
    window_start = alert.timestamp - timedelta(minutes=CORRELATION_WINDOW_MINUTES)
    window_end = alert.timestamp + timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    query = (
        db.query(Incident)
        .join(Alert, Alert.incident_id == Incident.id)
        .filter(Incident.status.notin_(["CLOSED"]))
        .filter(Alert.timestamp >= window_start, Alert.timestamp <= window_end)
    )

    if alert.source_ip:
        match = query.filter(Alert.source_ip == alert.source_ip).first()
        if match:
            return match
    if alert.username:
        match = query.filter(Alert.username == alert.username).first()
        if match:
            return match
    if alert.host:
        match = query.filter(Alert.host == alert.host).first()
        if match:
            return match
    return None


def _incident_title(alert: Alert) -> str:
    subject = alert.source_ip or alert.username or alert.host or "unknown source"
    return f"Security Incident: {alert.detection_rule.replace('_', ' ').title()} ({subject})"


def correlate_alerts(db: Session, alerts: list[Alert]) -> list[Incident]:
    touched_incidents: dict[str, Incident] = {}

    for alert in alerts:
        if alert.incident_id:
            continue

        incident = _find_related_incident(db, alert)
        if incident is None:
            incident = Incident(
                title=_incident_title(alert),
                description=alert.description,
                severity=alert.severity,
                status="OPEN",
                correlation_key=alert.source_ip or alert.username or alert.host,
            )
            db.add(incident)
            db.flush()
            logger.info("Created incident %s for alert %s", incident.id, alert.id)
        else:
            if SEVERITY_RANK.get(alert.severity, 0) > SEVERITY_RANK.get(incident.severity, 0):
                incident.severity = alert.severity

        alert.incident_id = incident.id
        db.flush()
        touched_incidents[incident.id] = incident

    return list(touched_incidents.values())
