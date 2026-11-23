"""Collects new events from a live Windows event log channel (default:
Security) using the built-in `wevtutil` tool - no extra dependencies.

A bookmark (the last EventRecordID sent) is persisted so a restart neither
resends nor skips events. It only advances on commit(), which the agent
calls once the events have been delivered - so events read while the
backend is unreachable are read again on the next poll, not lost. On
first start the collector begins at the
newest existing record, i.e. it forwards what happens from now on;
`--replay` resets the bookmark to send the channel's history instead.

Reading the Security channel requires an elevated (Administrator) process;
without it wevtutil reports "Access is denied" and this collector raises
PermissionError so the agent can explain and carry on with its files.

Each event's EventData is mapped to the backend's event schema, with the
same event-ID meanings as backend/app/services/parsing/windows_event.py.
"""
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

EVENT_NS = "http://schemas.microsoft.com/win/2004/08/events/event"
NS = {"e": EVENT_NS}
ET.register_namespace("", EVENT_NS)

# Keep in sync with EVENT_ID_MAP in backend/app/services/parsing/windows_event.py.
EVENT_ID_MAP = {
    4625: ("AUTH_FAILURE", "failed", "An account failed to log on"),
    4624: ("AUTH_SUCCESS", "success", "An account was successfully logged on"),
    4740: ("ACCOUNT_LOCKOUT", "locked", "A user account was locked out"),
    4720: ("USER_CREATED", "success", "A user account was created"),
    4672: ("PRIVILEGE_ASSIGNED", "success", "Special privileges assigned to new logon"),
    4648: ("EXPLICIT_CREDENTIAL_LOGON", "success", "A logon was attempted using explicit credentials"),
    1102: ("AUDIT_LOG_CLEARED", "success", "The audit log was cleared"),
}

# Logon types that represent a person or remote client logging on:
# 2 interactive, 3 network, 7 unlock, 8 network-cleartext, 10 RDP, 11 cached.
# Service (5) and batch (4) logons are routine system activity and skipped.
USER_LOGON_TYPES = {2, 3, 7, 8, 10, 11}
SYSTEM_ACCOUNTS = {"SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE", "ANONYMOUS LOGON", "-", ""}
SYSTEM_DOMAINS = {"NT AUTHORITY", "WINDOW MANAGER", "FONT DRIVER HOST"}

# A logon with no network source (console, runas, unlock, local API call)
# originated on this machine, so it is attributed to the loopback address.
# That keeps local password guessing visible to the backend's per-source
# brute-force rules instead of being dropped for lack of an IP.
LOCAL_SOURCE_PLACEHOLDERS = {"", "-", "::1", "127.0.0.1"}
LOCAL_SOURCE_IP = "127.0.0.1"

MAX_EVENTS_PER_POLL = 500


class WindowsEventCollector:
    def __init__(self, channel: str, event_ids: list[int], state_file: str) -> None:
        self.channel = channel
        self.event_ids = [int(i) for i in event_ids]
        self.state_file = state_file
        self.last_record_id: int | None = self._load_state()
        self._pending_record_id: int | None = None
        # Raw records returned by the last read, before noise filtering.
        self.records_read = 0

    def _load_state(self) -> int | None:
        try:
            with open(self.state_file) as f:
                return json.load(f).get(self.channel)
        except (OSError, json.JSONDecodeError):
            return None

    def _save_state(self) -> None:
        with open(self.state_file, "w") as f:
            json.dump({self.channel: self.last_record_id}, f)

    def reset(self) -> None:
        self.last_record_id = 0
        self._pending_record_id = None
        self._save_state()

    def commit(self) -> None:
        """Advance the bookmark past the events returned by the last read."""
        if self._pending_record_id is not None:
            self.last_record_id = self._pending_record_id
            self._pending_record_id = None
            self._save_state()

    def _wevtutil(self, *args: str) -> str:
        proc = subprocess.run(
            ["wevtutil", "qe", self.channel, *args, "/f:xml", "/e:Events"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout).strip()
            if "denied" in message.lower():
                raise PermissionError(
                    f"Access to the '{self.channel}' event log was denied - run the agent from an "
                    "elevated (Administrator) terminal to collect Windows Security events."
                )
            raise RuntimeError(f"wevtutil failed: {message}")
        return proc.stdout

    def _newest_record_id(self) -> int:
        events = ET.fromstring(self._wevtutil("/c:1", "/rd:true"))
        record = events.find("e:Event/e:System/e:EventRecordID", NS)
        return int(record.text) if record is not None else 0

    def read_new_events(self, max_events: int = MAX_EVENTS_PER_POLL) -> list[dict]:
        """Returns new events (oldest first) as dicts ready for POST
        /api/events. Call commit() once they have been delivered."""
        self.records_read = 0
        if self.last_record_id is None:
            self.last_record_id = self._newest_record_id()
            self._save_state()
            return []

        ids = " or ".join(f"EventID={i}" for i in self.event_ids)
        query = f"*[System[({ids}) and EventRecordID>{self.last_record_id}]]"
        events = ET.fromstring(self._wevtutil(f"/q:{query}", f"/c:{max_events}"))

        parsed: list[dict] = []
        pending = self.last_record_id
        for event in events.findall("e:Event", NS):
            self.records_read += 1
            record_id = int(event.findtext("e:System/e:EventRecordID", default="0", namespaces=NS))
            pending = max(pending, record_id)
            normalized = event_xml_to_dict(event)
            if normalized:
                parsed.append(normalized)
        self._pending_record_id = pending
        return parsed


def _parse_system_time(value: str | None) -> str | None:
    """'2026-09-25T18:25:55.6264255Z' -> ISO 8601 with at most microseconds."""
    if not value:
        return None
    value = value.rstrip("Z")
    if "." in value:
        whole, fraction = value.split(".", 1)
        value = f"{whole}.{fraction[:6]}"
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def event_xml_to_dict(event: ET.Element) -> dict | None:
    """Maps one <Event> element to the backend event schema, or None for
    events that are routine noise (service/system-account logons)."""
    event_id = int(event.findtext("e:System/e:EventID", default="0", namespaces=NS))
    event_type, status, description = EVENT_ID_MAP.get(event_id, (f"WINDOWS_EVENT_{event_id}", None, f"Windows event {event_id}"))

    # EventData (most events) or UserData (e.g. 1102) holds named fields.
    data = {d.get("Name"): (d.text or "").strip() for d in event.iter(f"{{{EVENT_NS}}}Data") if d.get("Name")}
    user_data = event.find("e:UserData", NS)
    if user_data is not None:
        for element in user_data.iter():
            if len(element) == 0 and element.text:
                data.setdefault(element.tag.split("}")[-1], element.text.strip())

    username = data.get("TargetUserName") or data.get("SubjectUserName") or None
    domain = data.get("TargetDomainName") or data.get("SubjectDomainName") or ""
    logon_type = int(data["LogonType"]) if data.get("LogonType", "").isdigit() else None

    if event_type == "AUTH_SUCCESS":
        if logon_type not in USER_LOGON_TYPES:
            return None
        if (username or "").upper() in SYSTEM_ACCOUNTS or (username or "").endswith("$") or domain.upper() in SYSTEM_DOMAINS:
            return None
        if username and (username.upper().startswith("DWM-") or username.upper().startswith("UMFD-")):
            return None

    source_ip = data.get("IpAddress")
    local_logon = False
    if event_type in ("AUTH_FAILURE", "AUTH_SUCCESS", "EXPLICIT_CREDENTIAL_LOGON"):
        if (source_ip or "") in LOCAL_SOURCE_PLACEHOLDERS:
            source_ip, local_logon = LOCAL_SOURCE_IP, True
    elif (source_ip or "") in LOCAL_SOURCE_PLACEHOLDERS:
        source_ip = None

    details = []
    if username:
        account = f"{domain}\\{username}" if domain and domain != "-" else username
        details.append(f"account {account}")
    if logon_type is not None:
        details.append(f"logon type {logon_type}")
    if data.get("FailureReason"):
        details.append(f"reason {data['FailureReason']}")
    if data.get("Status") and event_type == "AUTH_FAILURE":
        details.append(f"status {data['Status']}")
    message = f"{description}: {', '.join(details)}" if details else description

    time_created = event.find("e:System/e:TimeCreated", NS)
    return {
        "timestamp": _parse_system_time(time_created.get("SystemTime") if time_created is not None else None),
        "source_type": "WINDOWS_EVENT",
        "host": event.findtext("e:System/e:Computer", default=None, namespaces=NS),
        "source_ip": source_ip,
        "username": username,
        "event_type": event_type,
        "action": "logon" if event_id in (4624, 4625, 4648) else None,
        "status": status,
        "message": message[:2000],
        "raw_log": ET.tostring(event, encoding="unicode"),
        "metadata": {
            "event_id": event_id,
            "record_id": event.findtext("e:System/e:EventRecordID", default=None, namespaces=NS),
            "channel": event.findtext("e:System/e:Channel", default=None, namespaces=NS),
            "logon_type": logon_type,
            "workstation": data.get("WorkstationName"),
            "failure_status": data.get("Status") or None,
            "sub_status": data.get("SubStatus") or None,
            "local_logon": local_logon,
        },
    }


def is_supported_platform() -> bool:
    return os.name == "nt"
