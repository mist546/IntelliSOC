from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: str
    title: str
    severity: str
    confidence: float
    timestamp: datetime
    source_ip: str | None
    username: str | None
    host: str | None
    detection_rule: str
    description: str
    evidence: list
    status: str
    incident_id: str | None

    model_config = {"from_attributes": True}


class AlertStatusUpdate(BaseModel):
    status: str
