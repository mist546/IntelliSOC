from app.models.alert import Alert
from app.services.risk.engine import RiskResult, calculate_risk


def calculate_risk_tool(
    alert: Alert, threat_intel_results: list | None = None, anomaly_score: float | None = None, is_anomaly: bool = False
) -> RiskResult:
    return calculate_risk(alert, threat_intel_results=threat_intel_results, anomaly_score=anomaly_score, is_anomaly=is_anomaly)
