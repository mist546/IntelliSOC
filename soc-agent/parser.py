"""Minimal, self-contained log line parser for the endpoint agent.

Deliberately independent from the backend codebase (the agent is meant to
run on a separate host with no access to the backend's Python package), so
this duplicates a small, focused subset of the backend's auth.log parsing
logic. If you change detection-relevant fields here, keep them consistent
with backend/app/services/parsing/auth_log.py.
"""
import re
from datetime import datetime, timezone

SYSLOG_LINE_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<process>[\w.\-/]+)(?:\[(?P<pid>\d+)\])?:\s*"
    r"(?P<msg>.*)$"
)
FAILED_PASSWORD_RE = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+) port (?P<port>\d+)"
)
ACCEPTED_RE = re.compile(r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>[\d.:a-fA-F]+) port (?P<port>\d+)")


def _parse_timestamp(ts_str: str) -> datetime:
    year = datetime.now(timezone.utc).year
    try:
        return datetime.strptime(f"{year} {ts_str}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def parse_line(line: str, source_type: str) -> dict | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None

    if source_type not in ("AUTH_LOG", "SYSLOG"):
        # Other formats (Apache/Nginx/CSV/JSON) are parsed server-side when
        # uploaded via /api/logs/upload; the lightweight agent focuses on
        # line-oriented syslog-style sources it can tail in real time.
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
