"""Wazuh alert parser.

Wazuh agents ship logs to a Wazuh manager, which decodes them and writes one
JSON alert per line to /var/ossec/logs/alerts/alerts.json - or, with
logall_json, every decoded event to logs/archives/archives.json (the Docker
lab's Wazuh mode). The soc-agent forwards either file's lines to POST
/api/events/wazuh; an exported file can also be uploaded directly.

Each alert is mapped to the *underlying* source type (AUTH_LOG,
WINDOWS_EVENT, APACHE_ACCESS, NGINX_ACCESS) so the existing detection rules
apply unchanged. Wazuh's own context (rule, level, MITRE IDs, agent) is kept
in metadata["wazuh"]. Wazuh's own rule hits never become IntelliSOC alerts:
anything that is not one of the mapped log types is stored as a WAZUH event
only.

Wazuh writes each log line at most once, matched to its single deepest rule.
A frequency rule (5763 "sshd: brute force", 40112 "authentication success
after failures", ...) therefore carries a line that appears nowhere else, so
it is parsed like any other; its previous_output (the earlier lines) is not.
"""
import ipaddress
import json
import re

from dateutil.parser import isoparse

from app.services.parsing.auth_log import classify_auth_message
from app.services.parsing.base import ParsedEvent
from app.services.parsing.web_log import parse_access_log_line
from app.services.parsing.windows_event import _LOCAL_PLACEHOLDERS, EVENT_ID_MAP
from app.utils.time import to_naive_utc, utc_now

# Decoders / syslog programs whose lines go through the auth.log classifier.
AUTH_DECODERS = {"sshd", "sudo", "pam", "su", "login"}
AUTH_PROGRAMS = AUTH_DECODERS | {"sshd-session", "systemd-logind"}


def _timestamp(value):
    if isinstance(value, str) and value:
        try:
            return to_naive_utc(isoparse(value))
        except ValueError:
            pass
    return utc_now()


def _valid_ip(value) -> str | None:
    if not isinstance(value, str) or value.strip() in _LOCAL_PLACEHOLDERS:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _wazuh_context(alert: dict) -> dict:
    rule = alert.get("rule") or {}
    agent = alert.get("agent") or {}
    mitre = rule.get("mitre") or {}
    context = {
        "alert_id": alert.get("id"),
        "rule_id": rule.get("id"),
        "rule_level": rule.get("level"),
        "rule_description": rule.get("description"),
        "rule_groups": rule.get("groups"),
        "mitre_ids": mitre.get("id"),
        "agent_id": agent.get("id"),
        "agent_name": agent.get("name"),
        "agent_ip": agent.get("ip"),
        "location": alert.get("location"),
    }
    return {k: v for k, v in context.items() if v not in (None, "", [])}


def _windows_event(alert: dict, base: dict) -> ParsedEvent | None:
    win = (alert.get("data") or {}).get("win") or {}
    system = win.get("system") or {}
    eventdata = win.get("eventdata") or {}
    try:
        event_id = int(system.get("eventID"))
    except (TypeError, ValueError):
        return None
    event_type, status = EVENT_ID_MAP.get(event_id, (f"WINDOWS_EVENT_{event_id}", None))
    message = str(system.get("message") or "").strip().strip('"')
    first_line = message.splitlines()[0].strip() if message else (base["rule_description"] or f"Windows event {event_id}")
    username = eventdata.get("targetUserName")
    try:
        logon_type = int(eventdata["logonType"])
    except (KeyError, TypeError, ValueError):
        logon_type = None

    return ParsedEvent(
        timestamp=base["timestamp"],
        source_type="WINDOWS_EVENT",
        raw_log=json.dumps(alert),
        message=first_line[:2000],
        host=base["host"],
        source_ip=_valid_ip(eventdata.get("ipAddress")),
        destination_ip=base["destination_ip"],
        username=username if username and username != "-" else None,
        event_type=event_type,
        action="logon" if event_id in (4624, 4625, 4648) else None,
        status=status,
        metadata={
            "event_id": event_id,
            "logon_type": logon_type,
            "failure_reason": eventdata.get("failureReason"),
            "wazuh": base["context"],
        },
    )


def _web_event(alert: dict, base: dict) -> ParsedEvent | None:
    full_log = alert.get("full_log") or ""
    source_type = "NGINX_ACCESS" if "nginx" in str(alert.get("location", "")).lower() else "APACHE_ACCESS"
    event = parse_access_log_line(full_log, source_type)
    if event is None:
        return None
    event.host = base["host"]
    event.destination_ip = base["destination_ip"]
    event.metadata["wazuh"] = base["context"]
    return event


def _auth_event(alert: dict, base: dict, program: str | None) -> ParsedEvent:
    full_log = alert.get("full_log") or ""
    # Strip whatever syslog/journald header precedes "program[pid]: " - its
    # timestamp format varies by distro (classic vs. ISO 8601 on Ubuntu 23.10+).
    msg = full_log
    if program and (m := re.search(rf"{re.escape(program)}(?:\[\d+\])?:\s*(.*)$", full_log)):
        msg = m.group(1)
    event = ParsedEvent(
        timestamp=base["timestamp"],
        source_type="AUTH_LOG",
        raw_log=full_log,
        message=msg,
        host=base["host"],
        destination_ip=base["destination_ip"],
        event_type="AUTH_OTHER",
        metadata={"process": program, "wazuh": base["context"]},
    )
    return classify_auth_message(event, msg, program)


def parse_wazuh_alert(alert: dict) -> ParsedEvent | None:
    if not isinstance(alert, dict):
        return None
    # archives.json entries that matched no rule have no "rule" at all.
    rule = alert.get("rule", {})
    if not isinstance(rule, dict) or not (rule or alert.get("full_log") or alert.get("decoder")):
        return None

    agent = alert.get("agent") or {}
    decoder = alert.get("decoder") or {}
    predecoder = alert.get("predecoder") or {}
    base = {
        "timestamp": _timestamp(alert.get("timestamp")),
        "host": agent.get("name") or predecoder.get("hostname"),
        "destination_ip": _valid_ip(agent.get("ip")),
        "rule_description": rule.get("description"),
        "context": _wazuh_context(alert),
    }

    if ((alert.get("data") or {}).get("win") or {}).get("system"):
        event = _windows_event(alert, base)
        if event:
            return event
    if decoder.get("name") == "web-accesslog" and alert.get("full_log"):
        event = _web_event(alert, base)
        if event and event.event_type != "UNPARSED":
            return event
    program = predecoder.get("program_name")
    if alert.get("full_log") and (
        decoder.get("name") in AUTH_DECODERS or decoder.get("parent") in AUTH_DECODERS or program in AUTH_PROGRAMS
    ):
        return _auth_event(alert, base, program or decoder.get("parent") or decoder.get("name"))

    data = alert.get("data") or {}
    return ParsedEvent(
        timestamp=base["timestamp"],
        source_type="WAZUH",
        raw_log=alert.get("full_log") or json.dumps(alert),
        message=str(rule.get("description") or "Wazuh alert")[:2000],
        host=base["host"],
        source_ip=_valid_ip(data.get("srcip")),
        destination_ip=base["destination_ip"],
        username=data.get("srcuser") or data.get("dstuser"),
        event_type="WAZUH_ALERT" if rule else "WAZUH_EVENT",
        metadata={"wazuh": base["context"]},
    )


def _load_records(content: str, limit: int | None = None) -> list:
    text = content.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        records = data if isinstance(data, list) else [data]
        return records[:limit] if limit else records
    except json.JSONDecodeError:
        pass
    # alerts.json is NDJSON: one alert object per line.
    records = []
    for line in text.splitlines():
        if limit and len(records) >= limit:
            break
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def looks_like_wazuh_alerts(records: list) -> bool:
    sample = [r for r in records[:5] if isinstance(r, dict)]
    if not sample:
        return False
    # alerts.json lines all have a rule; archives.json lines may not, but
    # still carry the decoder or the original log line.
    return all(
        isinstance(r.get("agent"), dict)
        and (isinstance(r.get("rule"), dict) and "id" in r["rule"] or isinstance(r.get("decoder"), dict) or "full_log" in r)
        for r in sample
    )


def is_wazuh_alert_json(content: str) -> bool:
    return looks_like_wazuh_alerts(_load_records(content, limit=5))


def parse_wazuh_alerts(content: str) -> list[ParsedEvent]:
    events = []
    for record in _load_records(content):
        event = parse_wazuh_alert(record)
        if event:
            events.append(event)
    return events
