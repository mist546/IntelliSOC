from app.services.parsing.auth_log import SYSLOG_LINE_RE, _parse_timestamp
from app.services.parsing.base import ParsedEvent
from app.utils.time import utc_now


def parse_syslog_line(line: str) -> ParsedEvent | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None
    match = SYSLOG_LINE_RE.match(line)
    if not match:
        return ParsedEvent(
            timestamp=utc_now(),
            source_type="SYSLOG",
            raw_log=line,
            message=line,
            event_type="UNPARSED",
        )
    parts = match.groupdict()
    return ParsedEvent(
        timestamp=_parse_timestamp(parts["ts"]),
        source_type="SYSLOG",
        raw_log=line,
        message=parts["msg"],
        host=parts["host"],
        event_type="SYSTEM",
        metadata={"process": parts["process"]},
    )


def parse_syslog(content: str) -> list[ParsedEvent]:
    return [e for line in content.splitlines() if (e := parse_syslog_line(line))]
