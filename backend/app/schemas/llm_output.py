from pydantic import BaseModel, Field, field_validator


class LLMAnalysis(BaseModel):
    attack_type: str
    severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    evidence: list[str] = []
    threat_context: str = ""
    impact: str = ""
    mitre_technique: str | None = None
    owasp_category: str | None = None
    recommended_actions: list[str] = []
    requires_human_approval: bool = True
    insufficient_evidence: bool = False
    # [K] ids of the knowledge chunks that justify the analysis; checked
    # against what was actually provided by the investigator.
    references: list[str] = []

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"}
        upper = v.upper()
        return upper if upper in allowed else "UNKNOWN"
