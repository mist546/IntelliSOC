from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.log_event import LogEvent
from app.services.detection.auth_rules import (
    detect_excessive_auth_failures,
    detect_failed_then_success,
    detect_ssh_brute_force,
)
from app.services.detection.base import AlertDraft
from app.services.detection.web_rules import (
    detect_path_traversal,
    detect_sensitive_file_access,
    detect_sql_injection,
    detect_xss,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

RULES = [
    detect_ssh_brute_force,
    detect_failed_then_success,
    detect_excessive_auth_failures,
    detect_sql_injection,
    detect_xss,
    detect_path_traversal,
    detect_sensitive_file_access,
]


def _is_duplicate(db: Session, draft: AlertDraft) -> bool:
    if not draft.dedupe_key:
        return False
    window_start = draft.timestamp - timedelta(minutes=30)
    query = db.query(Alert).filter(
        Alert.detection_rule == draft.detection_rule,
        Alert.timestamp >= window_start,
        Alert.status.notin_(["RESOLVED", "FALSE_POSITIVE"]),
    )
    if draft.source_ip:
        query = query.filter(Alert.source_ip == draft.source_ip)
    if draft.username:
        query = query.filter(Alert.username == draft.username)
    return db.query(query.exists()).scalar()


def run_detection(db: Session, new_events: list[LogEvent]) -> list[Alert]:
    if not new_events:
        return []

    created: list[Alert] = []
    for rule_fn in RULES:
        try:
            drafts = rule_fn(db, new_events)
        except Exception:  # noqa: BLE001
            logger.exception("Detection rule %s failed", rule_fn.__name__)
            continue

        for draft in drafts:
            if _is_duplicate(db, draft):
                continue
            alert = Alert(
                title=draft.title,
                severity=draft.severity,
                confidence=draft.confidence,
                timestamp=draft.timestamp,
                source_ip=draft.source_ip,
                username=draft.username,
                host=draft.host,
                detection_rule=draft.detection_rule,
                description=draft.description,
                evidence=draft.evidence,
                related_event_ids=draft.related_event_ids,
                status="NEW",
            )
            db.add(alert)
            created.append(alert)

    if created:
        db.flush()
        logger.info("Detection engine created %d alert(s)", len(created))
    return created
