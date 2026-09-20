from dataclasses import dataclass, field


@dataclass
class ScanFinding:
    finding: str
    severity: str  # LOW | MEDIUM | HIGH
    evidence: str
    affected_url: str
    owasp_category: str
    description: str
    recommendation: str


@dataclass
class ScanOutcome:
    findings: list[ScanFinding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    error: str | None = None
