import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.log_event import LogEvent
from app.schemas.log_event import LogEventCreate
from app.services.correlation.correlator import correlate_alerts
from app.services.detection.engine import run_detection
from app.services.live_events import publish_event
from app.services.normalization.normalizer import normalize_to_log_event
from app.services.parsing import ParsedEvent, detect_source_type, parse_content
from app.utils.logging import get_logger
from app.utils.time import to_naive_utc, utc_now

logger = get_logger(__name__)


def _publish_ingestion(source: str, events_created: int, alerts, incidents) -> None:
    """Tell connected dashboards what just happened (called after commit)."""
    if events_created:
        publish_event("logs.ingested", {"source": source, "count": events_created})
    for alert in alerts:
        publish_event(
            "alert.created",
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity,
                "detection_rule": alert.detection_rule,
                "source_ip": alert.source_ip,
                "incident_id": alert.incident_id,
            },
        )
    for incident in incidents:
        publish_event("incident.updated", {"id": incident.id, "title": incident.title, "severity": incident.severity})


@dataclass
class IngestionResult:
    events_created: int = 0
    alerts_created: int = 0
    incidents_created: int = 0
    parse_errors: list[str] = field(default_factory=list)
    source_type: str = "UNKNOWN"


def ingest_raw_log(
    db: Session,
    content: str,
    filename: str,
    agent_id: str | None = None,
    source_type: str | None = None,
) -> IngestionResult:
    result = IngestionResult()

    detected_type = source_type or detect_source_type(filename, content)
    result.source_type = detected_type

    try:
        parsed_events = parse_content(content, detected_type)
    except ValueError as exc:
        result.parse_errors.append(str(exc))
        return result

    return ingest_parsed_events(db, parsed_events, source=filename, agent_id=agent_id, result=result)


def ingest_parsed_events(
    db: Session,
    parsed_events: list[ParsedEvent],
    source: str,
    agent_id: str | None = None,
    result: IngestionResult | None = None,
) -> IngestionResult:
    """Stores already-parsed events, then runs detection and correlation.
    Shared by file uploads and the Wazuh bridge endpoint."""
    if result is None:
        result = IngestionResult(source_type="MIXED")

    stored_events: list[LogEvent] = []
    for parsed in parsed_events:
        try:
            log_event = normalize_to_log_event(parsed, source=source, agent_id=agent_id)
            db.add(log_event)
            stored_events.append(log_event)
        except Exception as exc:  # noqa: BLE001
            result.parse_errors.append(str(exc))

    db.flush()
    result.events_created = len(stored_events)

    alerts = run_detection(db, stored_events)
    result.alerts_created = len(alerts)

    incidents = correlate_alerts(db, alerts)
    result.incidents_created = len(incidents)

    db.commit()
    _publish_ingestion(source, result.events_created, alerts, incidents)
    logger.info(
        "Ingested %d events from %s -> %d alerts, %d incidents",
        result.events_created, source, result.alerts_created, result.incidents_created,
    )
    return result


def ingest_normalized_events(
    db: Session,
    events: list[LogEventCreate],
    agent_id: str | None = None,
    default_source: str = "agent",
) -> IngestionResult:
    result = IngestionResult(source_type="MIXED")
    stored_events: list[LogEvent] = []

    for event in events:
        log_event = LogEvent(
            timestamp=to_naive_utc(event.timestamp) or utc_now(),
            source=event.source or default_source,
            source_type=event.source_type,
            host=event.host,
            source_ip=event.source_ip,
            destination_ip=event.destination_ip,
            username=event.username,
            event_type=event.event_type,
            action=event.action,
            status=event.status,
            message=event.message,
            raw_log=event.raw_log,
            metadata_=json.dumps(event.metadata) if event.metadata else None,
            agent_id=agent_id,
        )
        db.add(log_event)
        stored_events.append(log_event)

    db.flush()
    result.events_created = len(stored_events)

    alerts = run_detection(db, stored_events)
    result.alerts_created = len(alerts)

    incidents = correlate_alerts(db, alerts)
    result.incidents_created = len(incidents)

    db.commit()
    _publish_ingestion(default_source, result.events_created, alerts, incidents)
    return result
