import json
import re

from app.services.parsing.wazuh import is_wazuh_alert_json
from app.services.parsing.windows_event import looks_like_windows_events

AUTH_LOG_HINT = re.compile(r"sshd\[|sudo:|pam_unix")
APACHE_ACCESS_HINT = re.compile(r'"\w+ \S+ HTTP/\d\.\d"')
NGINX_ERROR_HINT = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} \[\w+\]")
APACHE_ERROR_HINT = re.compile(r"^\[\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2}")


def detect_source_type(filename: str, content: str) -> str:
    name = filename.lower()
    if name.endswith(".csv"):
        return "CSV"
    if name.endswith(".json"):
        return _json_source_type(content)

    sample = "\n".join(content.splitlines()[:30])

    # Checked before the text hints: Wazuh alerts embed raw sshd/access-log
    # lines in full_log, which would otherwise match AUTH_LOG_HINT etc.
    if sample.lstrip().startswith(("{", "[")) and is_wazuh_alert_json(content):
        return "WAZUH"
    if "auth" in name or AUTH_LOG_HINT.search(sample):
        return "AUTH_LOG"
    if "nginx" in name and "error" in name:
        return "NGINX_ERROR"
    if "nginx" in name:
        return "NGINX_ACCESS"
    if "apache" in name and "error" in name:
        return "APACHE_ERROR"
    if "apache" in name or "access" in name:
        return "APACHE_ACCESS"

    if APACHE_ACCESS_HINT.search(sample):
        return "APACHE_ACCESS"
    if NGINX_ERROR_HINT.search(sample):
        return "NGINX_ERROR"
    if APACHE_ERROR_HINT.search(sample):
        return "APACHE_ERROR"
    if sample.strip().startswith("{") or sample.strip().startswith("["):
        return _json_source_type(content)
    if "," in sample.splitlines()[0] if sample.splitlines() else False:
        return "CSV"

    return "SYSLOG"


def _json_source_type(content: str) -> str:
    if is_wazuh_alert_json(content):
        return "WAZUH"
    return "WINDOWS_EVENT" if _is_windows_event_json(content) else "JSON"


def _is_windows_event_json(content: str) -> bool:
    """A Windows Security export (Get-WinEvent | ConvertTo-Json) is JSON whose
    records carry an event Id and Message/TimeCreated - see windows_event.py."""
    text = content.strip()
    if not text:
        return False
    try:
        data = json.loads(text)
        records = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        records = []
        for line in text.splitlines()[:5]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                return False
    return looks_like_windows_events(records)
