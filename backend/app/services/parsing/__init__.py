from app.services.parsing.auth_log import parse_auth_log
from app.services.parsing.base import ParsedEvent
from app.services.parsing.detector import detect_source_type
from app.services.parsing.structured import parse_csv, parse_json_logs
from app.services.parsing.syslog import parse_syslog
from app.services.parsing.wazuh import parse_wazuh_alerts
from app.services.parsing.web_log import parse_access_log, parse_error_log
from app.services.parsing.windows_event import parse_windows_events

PARSERS = {
    "AUTH_LOG": lambda content: parse_auth_log(content, source_type="AUTH_LOG"),
    "SYSLOG": parse_syslog,
    "APACHE_ACCESS": lambda content: parse_access_log(content, source_type="APACHE_ACCESS"),
    "APACHE_ERROR": lambda content: parse_error_log(content, source_type="APACHE_ERROR"),
    "NGINX_ACCESS": lambda content: parse_access_log(content, source_type="NGINX_ACCESS"),
    "NGINX_ERROR": lambda content: parse_error_log(content, source_type="NGINX_ERROR"),
    "CSV": parse_csv,
    "JSON": parse_json_logs,
    "WINDOWS_EVENT": parse_windows_events,
    "WAZUH": parse_wazuh_alerts,
}


def parse_content(content: str, source_type: str) -> list[ParsedEvent]:
    parser = PARSERS.get(source_type)
    if parser is None:
        raise ValueError(f"Unsupported source_type: {source_type}")
    return parser(content)


__all__ = ["ParsedEvent", "PARSERS", "parse_content", "detect_source_type"]
