import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LogEventCreate(BaseModel):
    timestamp: datetime | None = None
    source: str
    source_type: str
    host: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    event_type: str
    action: str | None = None
    status: str | None = None
    message: str
    raw_log: str
    metadata: dict | None = None


class LogEventOut(BaseModel):
    id: str
    timestamp: datetime
    source: str
    source_type: str
    host: str | None
    source_ip: str | None
    destination_ip: str | None
    username: str | None
    event_type: str
    action: str | None
    status: str | None
    message: str
    raw_log: str
    # Parser-specific context, e.g. metadata["wazuh"] (rule, level, MITRE IDs,
    # agent) for events that arrived through a Wazuh manager. Stored as JSON
    # text in the "metadata" column (LogEvent.metadata_).
    metadata: dict | None = Field(default=None, validation_alias="metadata_")

    model_config = {"from_attributes": True}

    @field_validator("metadata", mode="before")
    @classmethod
    def _decode_metadata(cls, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return None
        return value if isinstance(value, dict) else None


class LogUploadResult(BaseModel):
    filename: str
    source_type: str
    events_created: int
    alerts_created: int
    incidents_created: int
    parse_errors: list[str] = []
