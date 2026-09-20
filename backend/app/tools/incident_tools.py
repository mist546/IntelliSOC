from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.incident import Incident


def search_previous_incidents(
    db: Session, source_ip: str | None = None, username: str | None = None, exclude_incident_id: str | None = None, limit: int = 5
) -> list[dict]:
    if not source_ip and not username:
        return []

    query = db.query(Incident).join(Alert, Alert.incident_id == Incident.id)
    if source_ip:
        query = query.filter(Alert.source_ip == source_ip)
    elif username:
        query = query.filter(Alert.username == username)
    if exclude_incident_id:
        query = query.filter(Incident.id != exclude_incident_id)

    incidents = query.distinct().order_by(Incident.created_at.desc()).limit(limit).all()
    return [
        {
            "id": i.id,
            "title": i.title,
            "severity": i.severity,
            "status": i.status,
            "created_at": i.created_at.isoformat(),
        }
        for i in incidents
    ]
