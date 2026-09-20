from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.models.log_event import LogEvent
from app.utils.logging import get_logger

logger = get_logger(__name__)

FEATURE_NAMES = ["event_count", "failed_login_count", "unique_usernames", "unique_event_types"]
MIN_BASELINE_IPS = 5


@dataclass
class AnomalyResult:
    anomaly_score: float | None
    is_anomaly: bool
    features: dict
    note: str = ""


def _features_for_ip(events: list[LogEvent]) -> dict:
    return {
        "event_count": len(events),
        "failed_login_count": sum(1 for e in events if e.event_type == "AUTH_FAILURE"),
        "unique_usernames": len({e.username for e in events if e.username}),
        "unique_event_types": len({e.event_type for e in events}),
    }


def compute_anomaly_score(db: Session, source_ip: str, reference_time, window_minutes: int = 120) -> AnomalyResult:
    """Supplementary, non-authoritative anomaly signal. Fits an Isolation
    Forest over the observed source IPs in the recent window and scores the
    target IP against that baseline. Never used on its own to declare an
    attack - only as one input into the deterministic risk engine.
    """
    if not source_ip:
        return AnomalyResult(anomaly_score=None, is_anomaly=False, features={}, note="No source IP to analyze")

    start_time = reference_time - timedelta(minutes=window_minutes)
    events = (
        db.query(LogEvent)
        .filter(LogEvent.timestamp >= start_time, LogEvent.timestamp <= reference_time)
        .all()
    )

    by_ip: dict[str, list[LogEvent]] = defaultdict(list)
    for e in events:
        if e.source_ip:
            by_ip[e.source_ip].append(e)

    if source_ip not in by_ip:
        return AnomalyResult(anomaly_score=None, is_anomaly=False, features={}, note="No events for this IP in window")

    if len(by_ip) < MIN_BASELINE_IPS:
        features = _features_for_ip(by_ip[source_ip])
        return AnomalyResult(
            anomaly_score=None,
            is_anomaly=False,
            features=features,
            note=f"Insufficient baseline ({len(by_ip)} distinct source IPs observed; need {MIN_BASELINE_IPS}+)",
        )

    ip_order = list(by_ip.keys())
    matrix = np.array([[_features_for_ip(by_ip[ip])[f] for f in FEATURE_NAMES] for ip in ip_order])

    try:
        model = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
        model.fit(matrix)
        target_idx = ip_order.index(source_ip)
        target_row = matrix[target_idx : target_idx + 1]
        raw_score = model.score_samples(target_row)[0]  # higher = more normal
        prediction = model.predict(target_row)[0]  # -1 anomaly, 1 normal

        all_scores = model.score_samples(matrix)
        lo, hi = all_scores.min(), all_scores.max()
        normalized = 0.5 if hi == lo else (hi - raw_score) / (hi - lo)  # 0=normal, 1=most anomalous

        return AnomalyResult(
            anomaly_score=round(float(normalized), 3),
            is_anomaly=bool(prediction == -1),
            features=_features_for_ip(by_ip[source_ip]),
            note=f"Scored against {len(ip_order)} distinct source IPs observed in the last {window_minutes} minutes",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Anomaly detection failed: %s", exc)
        return AnomalyResult(anomaly_score=None, is_anomaly=False, features={}, note=f"Anomaly detection unavailable: {exc}")
