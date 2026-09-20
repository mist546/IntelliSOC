from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AlertDraft:
    title: str
    severity: str
    confidence: float
    detection_rule: str
    description: str
    evidence: list[str]
    timestamp: datetime
    source_ip: str | None = None
    username: str | None = None
    host: str | None = None
    related_event_ids: list[str] = field(default_factory=list)
    dedupe_key: str = ""
