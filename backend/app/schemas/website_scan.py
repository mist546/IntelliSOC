from datetime import datetime

from pydantic import BaseModel


class ScanRequest(BaseModel):
    target_url: str


class ScanOut(BaseModel):
    id: str
    target_url: str
    status: str
    findings: list
    checks_run: list
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
