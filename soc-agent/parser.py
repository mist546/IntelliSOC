"""Minimal, self-contained log line parser for the endpoint agent.

Deliberately independent from the backend codebase (the agent is meant to
run on a separate host with no access to the backend's Python package), so
this duplicates a small, focused subset of the backend's auth.log parsing
logic. If you change detection-relevant fields here, keep them consistent
with backend/app/services/parsing/auth_log.py.
"""
import re
from datetime import datetime, timezone

# Two header timestamp styles:
#   classic:  "Jan 12 10:15:23 host sshd[2345]: ..."
#   RFC 3339: "2026-01-12T10:15:23.123456+05:00 host sshd[2345]: ..."
#             (rsyslog's default on Ubuntu 23.10+, Debian 13, ...)
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
ACCEPTED_RE = re.compile(r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+) port (?P<port>\d+)")
# Common/Combined Log Format (Apache and Nginx access logs). Mirrors
# ACCESS_LOG_RE in backend/app/services/parsing/web_log.py.
ACCESS_LOG_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+\S+"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)'
    r'(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)
ACCESS_SOURCE_TYPES = ("APACHE_ACCESS", "NGINX_ACCESS")
_FRACTION_RE = re.compile(r"(\.\d{6})\d+")
_COMPACT_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")


def _parse_iso_timestamp(ts_str: str) -> datetime:
    # fromisoformat() before Python 3.11 rejects "Z", >6 fraction digits and
    # "+0500"-style offsets, so normalise those first.
    value = _FRACTION_RE.sub(r"\1", ts_str.replace("Z", "+00:00"))
    value = _COMPACT_OFFSET_RE.sub(r"\1:\2", value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    # No offset: written in the host's local time, like classic syslog.
    return parsed.astimezone(timezone.utc)


def _parse_timestamp(ts_str: str) -> datetime:
    if ts_str[:1].isdigit():
        return _parse_iso_timestamp(ts_str)
    # Classic syslog timestamps carry no year or timezone and are written in
    # the host's local time, so interpret them as local time and convert to UTC.
    year = datetime.now().year
    try:
        local = datetime.strptime(f"{year} {ts_str}", "%Y %b %d %H:%M:%S")
    except ValueError:
        return datetime.now(timezone.utc)
    return local.astimezone(timezone.utc)


def _parse_access_line(line: str, source_type: str) -> dict:
    match = ACCESS_LOG_RE.match(line)
    if not match:
        return {"source_type": source_type, "event_type": "UNPARSED", "message": line, "raw_log": line}

    parts = match.groupdict()
    try:
        timestamp = datetime.strptime(parts["ts"], "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)
    except ValueError:
        timestamp = datetime.now(timezone.utc)
    # The web rules match attack patterns against the message, so it must
    # carry the full request path, as the backend's upload parser does.
    return {
        "timestamp": timestamp.isoformat(),
        "source_type": source_type,
        "event_type": "HTTP_REQUEST",
        "source_ip": parts["ip"],
        "username": None if parts["user"] == "-" else parts["user"],
        "action": parts["method"],
        "status": parts["status"],
        "message": f'{parts["method"]} {parts["path"]} -> {parts["status"]}',
        "raw_log": line,
        "metadata": {
            "path": parts["path"],
            "status_code": parts["status"],
            "size": parts["size"],
            "referrer": parts["referrer"],
            "user_agent": parts["agent"],
        },
    }


def parse_line(line: str, source_type: str) -> dict | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None

    if source_type in ACCESS_SOURCE_TYPES:
        return _parse_access_line(line, source_type)

    if source_type not in ("AUTH_LOG", "SYSLOG"):
        # Other formats (error logs/CSV/JSON) are parsed server-side when
        # uploaded via /api/logs/upload; the lightweight agent focuses on
        # line-oriented sources it can tail in real time.
        return {
            "source_type": source_type,
            "event_type": "GENERIC",
            "message": line[:2000],
            "raw_log": line,
        }

    match = SYSLOG_LINE_RE.match(line)
    if not match:
        return {"source_type": source_type, "event_type": "UNPARSED", "message": line, "raw_log": line}

    parts = match.groupdict()
    event = {
        "timestamp": _parse_timestamp(parts["ts"]).isoformat(),
        "source_type": source_type,
        "host": parts["host"],
        "event_type": "AUTH_OTHER" if source_type == "AUTH_LOG" else "SYSTEM",
        "message": parts["msg"],
        "raw_log": line,
    }

    if source_type == "AUTH_LOG":
        if (m := FAILED_PASSWORD_RE.search(parts["msg"])):
            event.update(event_type="AUTH_FAILURE", action="ssh_login", status="failure", username=m.group("user"), source_ip=m.group("ip"))
        elif (m := ACCEPTED_RE.search(parts["msg"])):
            event.update(event_type="AUTH_SUCCESS", action="ssh_login", status="success", username=m.group("user"), source_ip=m.group("ip"))

    return event
