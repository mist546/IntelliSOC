from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.log_event import LogEvent


def get_alert_details(db: Session, alert_id: str) -> dict | None:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None
    return {
        "id": alert.id,
        "title": alert.title,
        "severity": alert.severity,
        "confidence": alert.confidence,
        "detection_rule": alert.detection_rule,
        "description": alert.description,
        "evidence": alert.evidence,
        "source_ip": alert.source_ip,
        "username": alert.username,
        "host": alert.host,
        "status": alert.status,
        "timestamp": alert.timestamp.isoformat(),
        "related_event_ids": alert.related_event_ids,
    }


def get_related_events(db: Session, alert: Alert) -> list[dict]:
    if not alert.related_event_ids:
        return []
    events = db.query(LogEvent).filter(LogEvent.id.in_(alert.related_event_ids)).order_by(LogEvent.timestamp).all()
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "source_ip": e.source_ip,
            "username": e.username,
            "status": e.status,
            "message": e.message,
        }
        for e in events
    ]
