import json

from app.models.log_event import LogEvent
from app.services.parsing.base import ParsedEvent


def normalize_to_log_event(parsed: ParsedEvent, source: str, agent_id: str | None = None) -> LogEvent:
    return LogEvent(
        timestamp=parsed.timestamp,
        source=source,
        source_type=parsed.source_type,
        host=parsed.host,
        source_ip=parsed.source_ip,
        destination_ip=parsed.destination_ip,
        username=parsed.username,
        event_type=parsed.event_type,
        action=parsed.action,
        status=parsed.status,
        message=parsed.message,
        raw_log=parsed.raw_log,
        metadata_=json.dumps(parsed.metadata) if parsed.metadata else None,
        agent_id=agent_id,
    )
