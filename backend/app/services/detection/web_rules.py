import re
from urllib.parse import unquote

from app.models.log_event import LogEvent
from app.services.detection.base import AlertDraft

# Strong indicators: a single match is enough evidence on its own.
SQLI_STRONG_PATTERNS = [
    re.compile(r"\b(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|update\s+.*\s+set)\b", re.IGNORECASE),
    re.compile(r"\b(or|and)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?", re.IGNORECASE),
    re.compile(r"sleep\(\s*\d+\s*\)|benchmark\(", re.IGNORECASE),
    re.compile(r"information_schema|pg_sleep|xp_cmdshell", re.IGNORECASE),
]

# Weak indicators: common in legitimate requests, so require two or more together.
SQLI_WEAK_PATTERNS = [
    re.compile(r"(\%27)|(\')", re.IGNORECASE),
    re.compile(r"(\-\-)|(\%23)|(#)"),
]

XSS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"on(error|load|mouseover|click|focus)\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<img[^>]+src\s*=\s*['\"]?javascript:", re.IGNORECASE),
    re.compile(r"document\.(cookie|location)", re.IGNORECASE),
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
]

PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./|\.\.\\"),
    re.compile(r"%2e%2e%2f|%2e%2e/|\.\.%2f", re.IGNORECASE),
    re.compile(r"%252e%252e%252f", re.IGNORECASE),
    re.compile(r"\.\.%5c", re.IGNORECASE),
]

SENSITIVE_FILE_PATTERNS = [
    re.compile(r"/etc/passwd"),
    re.compile(r"/etc/shadow"),
    re.compile(r"\.env(\b|$)"),
    re.compile(r"wp-config\.php"),
    re.compile(r"id_rsa"),
    re.compile(r"\.git/config"),
    re.compile(r"web\.config"),
    re.compile(r"\.htpasswd"),
]


def _path_for(event: LogEvent) -> str:
    return unquote(event.message or "")


def _matches(patterns: list[re.Pattern], text: str) -> list[str]:
    return [p.pattern for p in patterns if p.search(text)]


def _http_events(events: list[LogEvent]) -> list[LogEvent]:
    return [e for e in events if e.event_type == "HTTP_REQUEST"]


def detect_sql_injection(db, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts = []
    for e in _http_events(new_events):
        text = _path_for(e)
        strong_hits = _matches(SQLI_STRONG_PATTERNS, text)
        weak_hits = _matches(SQLI_WEAK_PATTERNS, text)
        if not strong_hits and len(weak_hits) < 2:
            continue
        hits = strong_hits + weak_hits
        drafts.append(
            AlertDraft(
                title=f"Possible SQL Injection from {e.source_ip}",
                severity="HIGH",
                confidence=min(0.95, 0.5 + 0.15 * len(hits)),
                detection_rule="SQL_INJECTION",
                description=f"Request to {e.host or 'web server'} contained SQL injection indicators.",
                evidence=[f"Request: {e.message}", f"Matched patterns: {len(hits)}", f"Raw log: {e.raw_log}"],
                timestamp=e.timestamp,
                source_ip=e.source_ip,
                host=e.host,
                related_event_ids=[e.id],
                dedupe_key=f"SQL_INJECTION:{e.source_ip}:{e.id}",
            )
        )
    return drafts


def detect_xss(db, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts = []
    for e in _http_events(new_events):
        text = _path_for(e)
        hits = _matches(XSS_PATTERNS, text)
        if not hits:
            continue
        drafts.append(
            AlertDraft(
                title=f"Possible Cross-Site Scripting (XSS) from {e.source_ip}",
                severity="MEDIUM",
                confidence=min(0.9, 0.55 + 0.15 * len(hits)),
                detection_rule="XSS",
                description=f"Request to {e.host or 'web server'} contained XSS indicators.",
                evidence=[f"Request: {e.message}", f"Matched patterns: {len(hits)}", f"Raw log: {e.raw_log}"],
                timestamp=e.timestamp,
                source_ip=e.source_ip,
                host=e.host,
                related_event_ids=[e.id],
                dedupe_key=f"XSS:{e.source_ip}:{e.id}",
            )
        )
    return drafts


def detect_path_traversal(db, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts = []
    for e in _http_events(new_events):
        text = _path_for(e)
        hits = _matches(PATH_TRAVERSAL_PATTERNS, text)
        if not hits:
            continue
        drafts.append(
            AlertDraft(
                title=f"Possible Path Traversal from {e.source_ip}",
                severity="HIGH",
                confidence=min(0.92, 0.6 + 0.15 * len(hits)),
                detection_rule="PATH_TRAVERSAL",
                description=f"Request to {e.host or 'web server'} contained directory traversal indicators.",
                evidence=[f"Request: {e.message}", f"Matched patterns: {len(hits)}", f"Raw log: {e.raw_log}"],
                timestamp=e.timestamp,
                source_ip=e.source_ip,
                host=e.host,
                related_event_ids=[e.id],
                dedupe_key=f"PATH_TRAVERSAL:{e.source_ip}:{e.id}",
            )
        )
    return drafts


def detect_sensitive_file_access(db, new_events: list[LogEvent]) -> list[AlertDraft]:
    drafts = []
    for e in _http_events(new_events):
        text = _path_for(e)
        hits = _matches(SENSITIVE_FILE_PATTERNS, text)
        if not hits:
            continue
        status_code = (e.status or "").strip()
        severity = "HIGH" if status_code.startswith("2") else "MEDIUM"
        drafts.append(
            AlertDraft(
                title=f"Sensitive File Access Attempt from {e.source_ip}",
                severity=severity,
                confidence=0.85 if severity == "HIGH" else 0.6,
                detection_rule="SENSITIVE_FILE_ACCESS",
                description=(
                    f"Request to {e.host or 'web server'} targeted a sensitive file path "
                    f"(HTTP status {status_code or 'unknown'})."
                ),
                evidence=[f"Request: {e.message}", f"Matched pattern(s): {hits}", f"Raw log: {e.raw_log}"],
                timestamp=e.timestamp,
                source_ip=e.source_ip,
                host=e.host,
                related_event_ids=[e.id],
                dedupe_key=f"SENSITIVE_FILE_ACCESS:{e.source_ip}:{e.id}",
            )
        )
    return drafts
