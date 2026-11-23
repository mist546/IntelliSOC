"""Windows Security event log parser (optional input, spec section 7).

Windows does not write plain-text logs, so events are ingested from a JSON
export produced on the Windows host, e.g. (run as Administrator):

    Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624,4625,4740} -MaxEvents 500 |
        Select-Object Id, TimeCreated, MachineName, Message |
        ConvertTo-Json -Depth 3 | Out-File security_events.json -Encoding utf8

Each record carries the human-readable Message, from which the source IP,
target account and logon type are extracted. Only the fields the detection
engine needs are mapped; everything else is kept in metadata.
"""
import json
import re
from datetime import datetime, timezone

from app.services.parsing.base import ParsedEvent
from app.services.parsing.structured import _safe_timestamp

# Event ID -> (event_type, status). Anything else becomes WINDOWS_EVENT_<id>.
EVENT_ID_MAP = {
    4625: ("AUTH_FAILURE", "failed"),
    4624: ("AUTH_SUCCESS", "success"),
    4740: ("ACCOUNT_LOCKOUT", "locked"),
    4720: ("USER_CREATED", "success"),
    4672: ("PRIVILEGE_ASSIGNED", "success"),
    4648: ("EXPLICIT_CREDENTIAL_LOGON", "success"),
    1102: ("AUDIT_LOG_CLEARED", "success"),
}

# Logon types that never carry a meaningful network address.
_LOCAL_PLACEHOLDERS = {"-", "::1", "127.0.0.1", ""}

_ACCOUNT_RE = re.compile(r"Account Name:\s*([^\r\n]+)")
_SOURCE_IP_RE = re.compile(r"Source Network Address:\s*([^\r\n]+)")
_LOGON_TYPE_RE = re.compile(r"Logon Type:\s*(\d+)")
_FAILURE_REASON_RE = re.compile(r"Failure Reason:\s*([^\r\n]+)")
_PS_DATE_RE = re.compile(r"/Date\((\d+)\)/")


def _get(record: dict, *names):
    lowered = {str(k).lower(): v for k, v in record.items()}
    for name in names:
        if name.lower() in lowered and lowered[name.lower()] not in (None, ""):
            return lowered[name.lower()]
    return None


def _timestamp(value) -> datetime:
    # ConvertTo-Json serialises DateTime as "/Date(1695000000000)/" (ms since epoch).
    if isinstance(value, str):
        match = _PS_DATE_RE.search(value)
        if match:
            return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc).replace(tzinfo=None)
    return _safe_timestamp(value)


def _extract_from_message(message: str) -> dict:
    accounts = [a.strip() for a in _ACCOUNT_RE.findall(message)]
    # 4624/4625 messages list the *subject* account first and the *target*
    # (the account being logged on) second; prefer the target.
    target = next((a for a in reversed(accounts) if a and a != "-"), None)
    ip_match = _SOURCE_IP_RE.search(message)
    source_ip = ip_match.group(1).strip() if ip_match else None
    if source_ip in _LOCAL_PLACEHOLDERS:
        source_ip = None
    logon_type = _LOGON_TYPE_RE.search(message)
    reason = _FAILURE_REASON_RE.search(message)
    return {
        "username": target,
        "source_ip": source_ip,
        "logon_type": int(logon_type.group(1)) if logon_type else None,
        "failure_reason": reason.group(1).strip() if reason else None,
    }


def looks_like_windows_events(records: list[dict]) -> bool:
    """Heuristic used by the source-type detector: JSON records that carry a
    Windows event ID plus either a Message or a TimeCreated field."""
    sample = [r for r in records[:5] if isinstance(r, dict)]
    if not sample:
        return False
    return all(
        _get(r, "Id", "EventID", "EventId") is not None and (_get(r, "Message") is not None or _get(r, "TimeCreated") is not None)
        for r in sample
    )


def parse_windows_events(content: str) -> list[ParsedEvent]:
    content = content.strip()
    if not content:
        return []
    try:
        data = json.loads(content)
        records = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        records = []
        for line in content.splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    events: list[ParsedEvent] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_log = json.dumps(record)
        try:
            event_id = int(_get(record, "Id", "EventID", "EventId"))
        except (TypeError, ValueError):
            continue
        message = str(_get(record, "Message") or "")
        extracted = _extract_from_message(message)
        event_type, status = EVENT_ID_MAP.get(event_id, (f"WINDOWS_EVENT_{event_id}", None))
        first_line = message.splitlines()[0].strip() if message else f"Windows Security event {event_id}"

        events.append(
            ParsedEvent(
                timestamp=_timestamp(_get(record, "TimeCreated", "TimeGenerated", "timestamp")),
                source_type="WINDOWS_EVENT",
                raw_log=raw_log,
                message=first_line[:2000],
                host=_get(record, "MachineName", "Computer", "host"),
                source_ip=extracted["source_ip"] or _get(record, "IpAddress", "source_ip"),
                username=extracted["username"] or _get(record, "TargetUserName", "username"),
                event_type=event_type,
                action="logon" if event_id in (4624, 4625, 4648) else None,
                status=status,
                metadata={
                    "event_id": event_id,
                    "logon_type": extracted["logon_type"],
                    "failure_reason": extracted["failure_reason"],
                },
            )
        )
    return events
