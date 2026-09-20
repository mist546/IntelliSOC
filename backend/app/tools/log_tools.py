from datetime import datetime

from sqlalchemy.orm import Session

from app.models.log_event import LogEvent


def search_related_logs(
    db: Session,
    source_ip: str | None = None,
    username: str | None = None,
    host: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    query = db.query(LogEvent)
    if source_ip:
        query = query.filter(LogEvent.source_ip == source_ip)
    if username:
        query = query.filter(LogEvent.username == username)
    if host:
        query = query.filter(LogEvent.host == host)
    if event_type:
        query = query.filter(LogEvent.event_type == event_type)
    if start_time:
        query = query.filter(LogEvent.timestamp >= start_time)
    if end_time:
        query = query.filter(LogEvent.timestamp <= end_time)

    events = query.order_by(LogEvent.timestamp).limit(limit).all()
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
