import re
from datetime import datetime

from dateutil.parser import isoparse

from app.services.parsing.base import ParsedEvent
from app.utils.time import to_naive_utc, utc_now

# Jan 12 10:15:23 webserver01 sshd[2345]: message...
# 2026-01-12T10:15:23.123456+05:00 webserver01 sshd[2345]: message...
#   (RFC 3339 - rsyslog's default on Ubuntu 23.10+, Debian 13, ...)
SYSLOG_LINE_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r"|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<process>[\w.\-/]+)(?:\[(?P<pid>\d+)\])?:\s*"
    r"(?P<msg>.*)$"
)

FAILED_PASSWORD_RE = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+) port (?P<port>\d+)"
)
INVALID_USER_RE = re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+)")
ACCEPTED_RE = re.compile(r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+) port (?P<port>\d+)")
SESSION_OPENED_RE = re.compile(r"session opened for user (?P<user>\S+)")
SESSION_CLOSED_RE = re.compile(r"session closed for user (?P<user>\S+)")
SUDO_RE = re.compile(r"^\s*(?P<user>\S+)\s*:.*COMMAND=(?P<command>.*)$")


def _parse_timestamp(ts_str: str, reference_year: int | None = None) -> datetime:
    if ts_str[:1].isdigit():
        try:
            return to_naive_utc(isoparse(ts_str))
        except ValueError:
            return utc_now()
    year = reference_year or utc_now().year
    try:
        return datetime.strptime(f"{year} {ts_str}", "%Y %b %d %H:%M:%S")
    except ValueError:
        return utc_now()


def parse_auth_log_line(line: str, source_type: str = "AUTH_LOG") -> ParsedEvent | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None

    match = SYSLOG_LINE_RE.match(line)
    if not match:
        return ParsedEvent(
            timestamp=utc_now(),
            source_type=source_type,
            raw_log=line,
            message=line,
            event_type="UNPARSED",
        )

    parts = match.groupdict()
    timestamp = _parse_timestamp(parts["ts"])
    host = parts["host"]
    process = parts["process"]
    msg = parts["msg"]

    event = ParsedEvent(
        timestamp=timestamp,
        source_type=source_type,
        raw_log=line,
        message=msg,
        host=host,
        event_type="AUTH_OTHER",
        metadata={"process": process},
    )
    return classify_auth_message(event, msg, process)


def classify_auth_message(event: ParsedEvent, msg: str, process: str | None) -> ParsedEvent:
    """Sets event_type/action/status/username/source_ip from the message text
    alone, so callers that get the message without a classic syslog header
    (e.g. Wazuh alerts, whose full_log may carry an ISO timestamp) can reuse it."""
    if (m := FAILED_PASSWORD_RE.search(msg)):
        event.event_type = "AUTH_FAILURE"
        event.action = "ssh_login"
        event.status = "failure"
        event.username = m.group("user")
        event.source_ip = m.group("ip")
        return event

    if (m := INVALID_USER_RE.search(msg)):
        event.event_type = "AUTH_FAILURE"
        event.action = "ssh_login"
        event.status = "failure"
        event.username = m.group("user")
        event.source_ip = m.group("ip")
        return event

    if (m := ACCEPTED_RE.search(msg)):
        event.event_type = "AUTH_SUCCESS"
        event.action = "ssh_login"
        event.status = "success"
        event.username = m.group("user")
        event.source_ip = m.group("ip")
        return event

    if (m := SESSION_OPENED_RE.search(msg)):
        event.event_type = "SESSION_OPEN"
        event.action = "session_open"
        event.status = "success"
        event.username = m.group("user")
        return event

    if (m := SESSION_CLOSED_RE.search(msg)):
        event.event_type = "SESSION_CLOSE"
        event.action = "session_close"
        event.username = m.group("user")
        return event

    if process == "sudo" and (m := SUDO_RE.search(msg)):
        event.event_type = "PRIVILEGE_ESCALATION"
        event.action = "sudo"
        event.username = m.group("user")
        event.metadata["command"] = m.group("command")
        return event

    return event


def parse_auth_log(content: str, source_type: str = "AUTH_LOG") -> list[ParsedEvent]:
    events = []
    for line in content.splitlines():
        parsed = parse_auth_log_line(line, source_type=source_type)
        if parsed:
            events.append(parsed)
    return events
