"""Shapes a parsed line into the event schema expected by POST /api/events
(see backend/app/schemas/log_event.py: LogEventCreate)."""

REQUIRED_FIELDS = ("source_type", "event_type", "message", "raw_log")


def normalize(parsed: dict, source: str) -> dict | None:
    if not parsed or not all(f in parsed for f in REQUIRED_FIELDS):
        return None

    return {
        "timestamp": parsed.get("timestamp"),
        "source": source,
        "source_type": parsed["source_type"],
        "host": parsed.get("host"),
        "source_ip": parsed.get("source_ip"),
        "destination_ip": parsed.get("destination_ip"),
        "username": parsed.get("username"),
        "event_type": parsed["event_type"],
        "action": parsed.get("action"),
        "status": parsed.get("status"),
        "message": parsed["message"],
        "raw_log": parsed["raw_log"],
    }
