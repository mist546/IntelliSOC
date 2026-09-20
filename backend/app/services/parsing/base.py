from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedEvent:
    """timestamp is always naive and implicitly UTC - see app/utils/time.py
    for why this project does not use timezone-aware datetimes for anything
    stored in or compared against the database."""

    timestamp: datetime
    source_type: str
    raw_log: str
    message: str
    event_type: str = "UNKNOWN"
    host: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    action: str | None = None
    status: str | None = None
    metadata: dict = field(default_factory=dict)
