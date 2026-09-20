from datetime import datetime

from pydantic import BaseModel

from app.schemas.alert import AlertOut


class IncidentOut(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentDetailOut(IncidentOut):
    alerts: list[AlertOut] = []
