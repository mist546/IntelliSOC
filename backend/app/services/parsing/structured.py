import csv
import io
import json
from datetime import datetime, timezone

from dateutil import parser as date_parser  # provided by python-dateutil (fastapi dep)

from app.services.parsing.base import ParsedEvent
from app.utils.time import utc_now

KNOWN_FIELDS = {
    "timestamp", "source", "source_type", "host", "source_ip", "destination_ip",
    "username", "event_type", "action", "status", "message",
}


def _safe_timestamp(value) -> datetime:
    if not value:
        return utc_now()
    try:
        dt = date_parser.parse(str(value))
        # Normalize to naive UTC regardless of whether the source string
        # carried an offset - see app/utils/time.py.
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return utc_now()


def _row_to_event(row: dict, raw_log: str, source_type: str) -> ParsedEvent:
    extra = {k: v for k, v in row.items() if k not in KNOWN_FIELDS}
    return ParsedEvent(
        timestamp=_safe_timestamp(row.get("timestamp")),
        source_type=source_type,
        raw_log=raw_log,
        message=str(row.get("message") or raw_log)[:2000],
        host=row.get("host"),
        source_ip=row.get("source_ip") or row.get("src_ip") or row.get("ip"),
        destination_ip=row.get("destination_ip") or row.get("dst_ip"),
        username=row.get("username") or row.get("user"),
        event_type=str(row.get("event_type") or "GENERIC").upper(),
        action=row.get("action"),
        status=row.get("status"),
        metadata=extra,
    )


def parse_csv(content: str) -> list[ParsedEvent]:
    events = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        raw_log = ",".join(f"{k}={v}" for k, v in row.items())
        events.append(_row_to_event(row, raw_log, "CSV"))
    return events


def parse_json_logs(content: str) -> list[ParsedEvent]:
    content = content.strip()
    if not content:
        return []

    records: list[dict] = []
    try:
        data = json.loads(content)
        records = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    events = []
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_log = json.dumps(record)
        events.append(_row_to_event(record, raw_log, "JSON"))
    return events
