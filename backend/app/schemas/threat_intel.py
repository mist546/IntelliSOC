from datetime import datetime

from pydantic import BaseModel


class ThreatIntelOut(BaseModel):
    indicator: str
    indicator_type: str
    reputation: str
    classification: str | None
    source: str
    confidence: float
    details: dict
    timestamp: datetime | None = None

    model_config = {"from_attributes": True}
