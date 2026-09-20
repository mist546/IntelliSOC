from datetime import datetime

from pydantic import BaseModel

from app.schemas.llm_output import LLMAnalysis


class InvestigationOut(BaseModel):
    id: str
    alert_id: str | None
    incident_id: str | None
    status: str
    trace: list
    evidence: dict
    threat_intelligence: list
    rag_sources: list
    risk_score: float | None
    risk_factors: list
    ai_analysis: dict | None
    llm_available: bool
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class InvestigationTraceOut(BaseModel):
    id: str
    status: str
    trace: list


class InvestigateRequest(BaseModel):
    force: bool = False
