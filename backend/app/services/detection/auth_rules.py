from collections import defaultdict
from datetime import timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.log_event import LogEvent
from app.services.detection.base import AlertDraft

settings = get_settings()

# Sources whose AUTH_FAILURE / AUTH_SUCCESS events represent interactive or
# network logons and therefore feed the brute-force rules.
AUTH_SOURCE_TYPES = ("AUTH_LOG", "WINDOWS_EVENT")


def _auth_label(source_type: str) -> str:
    return "Windows logon" if source_type == "WINDOWS_EVENT" else "SSH"


def _failures_in_window(db: Session, source_ip: str, end_time, window_minutes: int) -> list[LogEvent]:
    start_time = end_time - timedelta(minutes=window_minutes)
    return (
        db.query(LogEvent)
        .filter(
            and_(
                LogEvent.source_ip == source_ip,
                LogEvent.event_type == "AUTH_FAILURE",
                LogEvent.timestamp >= start_time,
                LogEvent.timestamp <= end_time,
            )
        )
        .order_by(LogEvent.timestamp)
        .all()
    )


def detect_ssh_brute_force(db: Session, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts: list[AlertDraft] = []
    threshold = settings.SSH_BRUTE_FORCE_THRESHOLD
    window = settings.SSH_BRUTE_FORCE_WINDOW_MINUTES

    candidate_ips = {
        e.source_ip
        for e in new_events
        if e.event_type == "AUTH_FAILURE" and e.source_ip and e.source_type in AUTH_SOURCE_TYPES
    }

    for ip in candidate_ips:
        latest = max(
            (e.timestamp for e in new_events if e.source_ip == ip and e.event_type == "AUTH_FAILURE"),
        )
        failures = _failures_in_window(db, ip, latest, window)
        if len(failures) < threshold:
            continue

        usernames = sorted({f.username for f in failures if f.username})
        label = _auth_label(failures[-1].source_type)
        drafts.append(
            AlertDraft(
                title=f"{label} Brute Force from {ip}",
                severity="HIGH",
                confidence=min(0.99, 0.6 + 0.01 * len(failures)),
                detection_rule="SSH_BRUTE_FORCE",
                description=(
                    f"{len(failures)} failed {label} authentication attempts from {ip} "
                    f"within a {window}-minute window."
                ),
                evidence=[
                    f"{len(failures)} failed {label} authentication attempts observed",
                    f"Same source IP ({ip}) observed repeatedly within {window} minutes",
                    f"Usernames targeted: {', '.join(usernames) if usernames else 'unknown'}",
                ],
                timestamp=latest,
                source_ip=ip,
                username=usernames[0] if len(usernames) == 1 else None,
                host=failures[-1].host,
                related_event_ids=[f.id for f in failures],
                dedupe_key=f"SSH_BRUTE_FORCE:{ip}",
            )
        )
    return drafts


def detect_failed_then_success(db: Session, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts: list[AlertDraft] = []
    window = settings.SSH_BRUTE_FORCE_WINDOW_MINUTES
    min_failures = 3

    successes = [
        e for e in new_events if e.event_type == "AUTH_SUCCESS" and e.source_ip and e.source_type in AUTH_SOURCE_TYPES
    ]

    for success in successes:
        failures = _failures_in_window(db, success.source_ip, success.timestamp, window)
        failures = [f for f in failures if f.timestamp <= success.timestamp]
        if len(failures) < min_failures:
            continue

        severity = "CRITICAL" if len(failures) >= settings.SSH_BRUTE_FORCE_THRESHOLD else "HIGH"
        drafts.append(
            AlertDraft(
                title=f"Successful Login After Failed Attempts from {success.source_ip}",
                severity=severity,
                confidence=min(0.97, 0.65 + 0.02 * len(failures)),
                detection_rule="FAILED_THEN_SUCCESS",
                description=(
                    f"{len(failures)} failed authentication attempts from {success.source_ip} "
                    f"were followed by a successful login as '{success.username}', suggesting possible "
                    f"credential compromise."
                ),
                evidence=[
                    f"{len(failures)} failed login attempts preceded the successful login",
                    f"Successful login as '{success.username}' at {success.timestamp.isoformat()}",
                    f"Same source IP ({success.source_ip}) for both failures and success",
                ],
                timestamp=success.timestamp,
                source_ip=success.source_ip,
                username=success.username,
                host=success.host,
                related_event_ids=[f.id for f in failures] + [success.id],
                dedupe_key=f"FAILED_THEN_SUCCESS:{success.source_ip}:{success.username}",
            )
        )
    return drafts


def detect_excessive_auth_failures(db: Session, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts: list[AlertDraft] = []
    window = 15
    threshold = 15

    by_user: dict[str, list[LogEvent]] = defaultdict(list)
    for e in new_events:
        if e.event_type == "AUTH_FAILURE" and e.username:
            by_user[e.username].append(e)

    for username, events in by_user.items():
        latest = max(e.timestamp for e in events)
        start_time = latest - timedelta(minutes=window)
        all_failures = (
            db.query(LogEvent)
            .filter(
                and_(
                    LogEvent.username == username,
                    LogEvent.event_type == "AUTH_FAILURE",
                    LogEvent.timestamp >= start_time,
                    LogEvent.timestamp <= latest,
                )
            )
            .all()
        )
        if len(all_failures) < threshold:
            continue

        unique_ips = sorted({f.source_ip for f in all_failures if f.source_ip})
        drafts.append(
            AlertDraft(
                title=f"Excessive Authentication Failures for '{username}'",
                severity="MEDIUM" if len(unique_ips) <= 1 else "HIGH",
                confidence=0.7,
                detection_rule="EXCESSIVE_AUTH_FAILURES",
                description=(
                    f"{len(all_failures)} authentication failures for account '{username}' "
                    f"within {window} minutes across {len(unique_ips)} source IP(s)."
                ),
                evidence=[
                    f"{len(all_failures)} failed authentication attempts for '{username}'",
                    f"Observed from {len(unique_ips)} distinct source IP(s): {', '.join(unique_ips) or 'unknown'}",
                ],
                timestamp=latest,
                username=username,
                source_ip=unique_ips[0] if len(unique_ips) == 1 else None,
                related_event_ids=[f.id for f in all_failures],
                dedupe_key=f"EXCESSIVE_AUTH_FAILURES:{username}",
            )
        )
    return drafts
