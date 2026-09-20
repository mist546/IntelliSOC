import re
from datetime import datetime, timezone

from app.services.parsing.base import ParsedEvent
from app.utils.time import utc_now

# Common/Combined Log Format used by both Apache and Nginx access logs.
ACCESS_LOG_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+\S+"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)'
    r'(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)

APACHE_ERROR_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+\[[^\]]*\]\s+\[pid\s+\d+\]\s+(?:\[client\s+(?P<ip>[\d.:a-fA-F]+)(?::\d+)?\]\s+)?(?P<msg>.*)$"
)

NGINX_ERROR_RE = re.compile(
    r"^(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(?P<level>\w+)\]\s+\d+#\d+:\s+\*?\d*\s*(?P<msg>.*)$"
)

NGINX_ERROR_CLIENT_RE = re.compile(r"client:\s*(?P<ip>[\d.:a-fA-F]+)")


def _parse_access_ts(ts_str: str) -> datetime:
    try:
        # %z parses the log's own UTC offset; normalize to UTC and drop
        # tzinfo so this value is comparable with every other timestamp in
        # the system (see app/utils/time.py).
        aware = datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z")
        return aware.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return utc_now()


def parse_access_log_line(line: str, source_type: str) -> ParsedEvent | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None

    match = ACCESS_LOG_RE.match(line)
    if not match:
        return ParsedEvent(
            timestamp=utc_now(),
            source_type=source_type,
            raw_log=line,
            message=line,
            event_type="UNPARSED",
        )

    parts = match.groupdict()
    status_code = parts["status"]
    path = parts["path"]
    method = parts["method"]

    return ParsedEvent(
        timestamp=_parse_access_ts(parts["ts"]),
        source_type=source_type,
        raw_log=line,
        message=f'{method} {path} -> {status_code}',
        source_ip=parts["ip"],
        username=None if parts["user"] == "-" else parts["user"],
        event_type="HTTP_REQUEST",
        action=method,
        status=status_code,
        metadata={
            "path": path,
            "status_code": status_code,
            "size": parts.get("size"),
            "referrer": parts.get("referrer"),
            "user_agent": parts.get("agent"),
        },
    )


def parse_access_log(content: str, source_type: str) -> list[ParsedEvent]:
    return [e for line in content.splitlines() if (e := parse_access_log_line(line, source_type))]


def parse_error_log_line(line: str, source_type: str) -> ParsedEvent | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None

    if source_type == "APACHE_ERROR":
        match = APACHE_ERROR_RE.match(line)
        if match:
            parts = match.groupdict()
            return ParsedEvent(
                timestamp=utc_now(),
                source_type=source_type,
                raw_log=line,
                message=parts["msg"],
                source_ip=parts.get("ip"),
                event_type="WEB_ERROR",
            )
    else:
        match = NGINX_ERROR_RE.match(line)
        if match:
            parts = match.groupdict()
            client_match = NGINX_ERROR_CLIENT_RE.search(parts["msg"])
            return ParsedEvent(
                timestamp=utc_now(),
                source_type=source_type,
                raw_log=line,
                message=parts["msg"],
                source_ip=client_match.group("ip") if client_match else None,
                event_type="WEB_ERROR",
                metadata={"level": parts.get("level")},
            )

    return ParsedEvent(
        timestamp=utc_now(),
        source_type=source_type,
        raw_log=line,
        message=line,
        event_type="UNPARSED",
    )


def parse_error_log(content: str, source_type: str) -> list[ParsedEvent]:
    return [e for line in content.splitlines() if (e := parse_error_log_line(line, source_type))]
