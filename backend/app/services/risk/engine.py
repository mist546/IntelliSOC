from dataclasses import dataclass, field

from app.models.alert import Alert
from app.services.threat_intel.base import ThreatIntelResult

SEVERITY_BASE_SCORE = {"LOW": 20, "MEDIUM": 40, "HIGH": 65, "CRITICAL": 85}

COMPROMISE_INDICATOR_RULES = {"FAILED_THEN_SUCCESS"}


@dataclass
class RiskResult:
    risk_score: float
    severity: str
    confidence: float
    risk_factors: list[str] = field(default_factory=list)


def _severity_from_score(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def calculate_risk(
    alert: Alert,
    threat_intel_results: list[ThreatIntelResult] | None = None,
    anomaly_score: float | None = None,
    is_anomaly: bool = False,
) -> RiskResult:
    """Deterministic, transparent risk scoring (0-100). Every contribution
    to the score is recorded in risk_factors so an analyst (and the LLM)
    can see exactly why a score was produced. The LLM must not override
    this score without evidence-based justification.
    """
    threat_intel_results = threat_intel_results or []
    factors: list[str] = []

    score = SEVERITY_BASE_SCORE.get(alert.severity, 20)
    factors.append(f"Base score {score} from detection severity '{alert.severity}'")

    evidence_count = len(alert.evidence or [])
    evidence_bonus = min(15, evidence_count * 3)
    if evidence_bonus:
        score += evidence_bonus
        factors.append(f"+{evidence_bonus} for {evidence_count} evidence item(s) supporting the alert")

    if alert.detection_rule in COMPROMISE_INDICATOR_RULES:
        score += 20
        factors.append("+20 for a strong compromise indicator (failed attempts followed by success)")

    max_ti_confidence = 0.0
    for ti in threat_intel_results:
        if ti.reputation == "malicious":
            bonus = round(15 * ti.confidence)
            score += bonus
            factors.append(f"+{bonus} for malicious threat intelligence verdict from {ti.source} (indicator {ti.indicator})")
            max_ti_confidence = max(max_ti_confidence, ti.confidence)
        elif ti.reputation == "suspicious":
            bonus = round(7 * ti.confidence)
            score += bonus
            factors.append(f"+{bonus} for suspicious threat intelligence verdict from {ti.source} (indicator {ti.indicator})")
            max_ti_confidence = max(max_ti_confidence, ti.confidence * 0.6)

    if anomaly_score is not None and is_anomaly:
        score += 10
        factors.append(f"+10 for ML anomaly detector flagging this activity (anomaly_score={anomaly_score:.2f})")
    elif anomaly_score is not None:
        factors.append(f"ML anomaly detector did not flag this activity (anomaly_score={anomaly_score:.2f}, informational only)")

    score = max(0, min(100, score))
    severity = _severity_from_score(score)

    confidence = round((alert.confidence + max(max_ti_confidence, 0.5)) / 2, 2)
    confidence = max(0.0, min(1.0, confidence))

    return RiskResult(risk_score=score, severity=severity, confidence=confidence, risk_factors=factors)
