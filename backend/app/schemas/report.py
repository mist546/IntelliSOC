from datetime import datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: str
    incident_id: str
    format: str
    file_path: str | None
    content: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportRequest(BaseModel):
    format: str = "json"  # json | pdf
