---
title: Response Playbooks - SQL Injection, XSS, Path Traversal, Sensitive File Access
category: playbook
source: Internal Mini-SOC playbook (derived from OWASP guidance)
---

# Response Playbook: SQL Injection

Applies to detection rule `SQL_INJECTION`. Maps to OWASP A03:2021 (Injection)
and CWE-89, MITRE T1190 (Exploit Public-Facing Application).

**Investigation steps**: identify the affected endpoint and parameter,
review the exact payload for syntax indicating tautologies, UNION-based
extraction, or time-based blind injection (e.g. `SLEEP()`), and check
database logs for unusual queries around the same timestamp.

**Recommended actions**: inspect the affected endpoint and its input
handling; inspect the request parameters and full payload; review database
audit logs for unauthorized queries; validate and parameterize all
database-facing input; patch the vulnerable application code; escalate if
data exfiltration or modification is confirmed.

# Response Playbook: Cross-Site Scripting (XSS)

Applies to detection rule `XSS`. Maps to OWASP A03:2021 (Injection) and
CWE-79.

**Investigation steps**: identify whether the payload was reflected in a
response (reflected XSS) or appears intended for storage (stored XSS,
higher severity since it affects all future visitors). Review whether any
session tokens or cookies may have been exposed.

**Recommended actions**: inspect the affected endpoint and output encoding;
review session/user impact, particularly for stored XSS; apply
context-aware output encoding and a Content-Security-Policy; patch the
application.

# Response Playbook: Path Traversal

Applies to detection rule `PATH_TRAVERSAL`. Maps to OWASP A01:2021 (Broken
Access Control) and CWE-22.

**Investigation steps**: determine which file path was actually requested
after normalization, whether the HTTP response indicates success (2xx) or
failure, and whether the target path could reach sensitive files or source
code.

**Recommended actions**: inspect the requested path and server response
code; determine whether sensitive data was exposed (check response size and
status); review broader server activity from the same source; patch the
path-handling logic to canonicalize and validate against an allow-list;
escalate if exposure of sensitive data is confirmed.

# Response Playbook: Sensitive File Access

Applies to detection rule `SENSITIVE_FILE_ACCESS`. Maps to OWASP A01:2021
and CWE-200/CWE-798.

**Investigation steps**: check the HTTP status code returned - a 2xx
response to a request for `/etc/passwd`, `.env`, or similar indicates the
file may have actually been served, which is far more severe than a 403/404
response indicating the request was blocked.

**Recommended actions**: same as Path Traversal above; additionally rotate
any credentials that may have been present in an exposed configuration
file.
