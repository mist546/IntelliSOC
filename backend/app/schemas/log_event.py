from datetime import datetime

from pydantic import BaseModel


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

    model_config = {"from_attributes": True}


class LogUploadResult(BaseModel):
    filename: str
    source_type: str
    events_created: int
    alerts_created: int
    incidents_created: int
    parse_errors: list[str] = []
