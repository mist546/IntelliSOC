import re
import uuid
from urllib.parse import urlparse

import httpx

from app.services.scanning.base import ScanFinding

SENSITIVE_PATHS = [
    "/.env",
    "/.git/config",
    "/wp-config.php.bak",
    "/config.php.bak",
    "/.htpasswd",
    "/server-status",
    "/backup.zip",
    "/.aws/credentials",
]

SQL_ERROR_SIGNATURES = [
    "sql syntax", "mysql_fetch", "ora-01756", "unclosed quotation mark",
    "sqlite3.operationalerror", "pg_query", "syntax error at or near",
    "warning: mysqli", "microsoft odbc",
]

REQUIRED_HEADERS = {
    "strict-transport-security": ("Strict-Transport-Security header missing", "A02:2021"),
    "x-content-type-options": ("X-Content-Type-Options header missing", "A05:2021"),
    "x-frame-options": ("X-Frame-Options header missing (clickjacking risk)", "A05:2021"),
    "content-security-policy": ("Content-Security-Policy header missing", "A05:2021"),
    "referrer-policy": ("Referrer-Policy header missing", "A05:2021"),
}


def check_security_headers(headers: httpx.Headers, url: str) -> list[ScanFinding]:
    findings = []
    lower_headers = {k.lower() for k in headers.keys()}
    for header, (message, owasp) in REQUIRED_HEADERS.items():
        if header not in lower_headers:
            findings.append(
                ScanFinding(
                    finding=message,
                    severity="LOW",
                    evidence=f"Response headers did not include '{header}'",
                    affected_url=url,
                    owasp_category=owasp,
                    description="Missing security headers reduce defense-in-depth against common browser-based attacks.",
                    recommendation=f"Configure the web server/application to send a '{header}' header.",
                )
            )
    return findings


def check_server_banner(headers: httpx.Headers, url: str) -> list[ScanFinding]:
    findings = []
    for header in ("server", "x-powered-by"):
        value = headers.get(header)
        if value:
            findings.append(
                ScanFinding(
                    finding=f"Server version/technology disclosure via '{header}' header",
                    severity="LOW",
                    evidence=f"{header}: {value}",
                    affected_url=url,
                    owasp_category="A05:2021",
                    description="Revealing server/framework versions helps attackers target known vulnerabilities.",
                    recommendation=f"Suppress or genericize the '{header}' response header.",
                )
            )
    return findings


def check_cleartext_transport(url: str) -> list[ScanFinding]:
    parsed = urlparse(url)
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
        return [
            ScanFinding(
                finding="Site served over cleartext HTTP",
                severity="MEDIUM",
                evidence=f"Target scheme is 'http' for {parsed.hostname}",
                affected_url=url,
                owasp_category="A02:2021",
                description="Traffic sent over HTTP can be intercepted or modified in transit.",
                recommendation="Serve the application exclusively over HTTPS with HSTS enabled.",
            )
        ]
    return []


def check_cookies(resp: httpx.Response, url: str) -> list[ScanFinding]:
    findings = []
    for cookie_header in resp.headers.get_list("set-cookie"):
        lower = cookie_header.lower()
        missing = [flag for flag in ("secure", "httponly", "samesite") if flag not in lower]
        if missing:
            cookie_name = cookie_header.split("=")[0]
            findings.append(
                ScanFinding(
                    finding=f"Cookie '{cookie_name}' missing security flag(s): {', '.join(missing)}",
                    severity="LOW",
                    evidence=cookie_header[:200],
                    affected_url=url,
                    owasp_category="A05:2021",
                    description="Cookies without Secure/HttpOnly/SameSite flags are more exposed to theft or CSRF.",
                    recommendation="Set Secure, HttpOnly, and SameSite attributes on all session cookies.",
                )
            )
    return findings


def check_sensitive_paths(client: httpx.Client, base_url: str) -> list[ScanFinding]:
    findings = []
    for path in SENSITIVE_PATHS:
        target = base_url.rstrip("/") + path
        try:
            resp = client.get(target, timeout=client.timeout)
        except httpx.HTTPError:
            continue
        if resp.status_code == 200:
            findings.append(
                ScanFinding(
                    finding=f"Potentially sensitive file accessible: {path}",
                    severity="HIGH",
                    evidence=f"GET {path} returned HTTP {resp.status_code}",
                    affected_url=target,
                    owasp_category="A01:2021",
                    description="A sensitive configuration or backup file appears to be publicly accessible.",
                    recommendation="Remove or restrict access to this file; verify it does not leak secrets.",
                )
            )
    return findings


def check_reflected_xss(client: httpx.Client, base_url: str) -> list[ScanFinding]:
    canary = f"soc{uuid.uuid4().hex[:8]}<b>x</b>"
    target = f"{base_url.rstrip('/')}/?q={canary}"
    try:
        resp = client.get(target, timeout=client.timeout)
    except httpx.HTTPError:
        return []
    if canary in resp.text:
        return [
            ScanFinding(
                finding="Possible reflected input without output encoding",
                severity="MEDIUM",
                evidence=f"Query parameter value was reflected unescaped in the response body for {target}",
                affected_url=target,
                owasp_category="A03:2021",
                description="Unencoded reflection of user input is a precondition for reflected XSS.",
                recommendation="Apply context-aware output encoding to all reflected user input.",
            )
        ]
    return []


def check_sql_error_disclosure(client: httpx.Client, base_url: str) -> list[ScanFinding]:
    target = f"{base_url.rstrip('/')}/?id=1'"
    try:
        resp = client.get(target, timeout=client.timeout)
    except httpx.HTTPError:
        return []
    body_lower = resp.text.lower()
    for signature in SQL_ERROR_SIGNATURES:
        if signature in body_lower:
            return [
                ScanFinding(
                    finding="Database error message disclosed in response",
                    severity="HIGH",
                    evidence=f"Response to a single-quote probe contained the signature '{signature}'",
                    affected_url=target,
                    owasp_category="A03:2021",
                    description="Verbose database errors can reveal query structure and hint at SQL injection.",
                    recommendation="Disable verbose error output in production and validate/parameterize all input.",
                )
            ]
    return []
