---
title: Internal Detection Rules Reference
category: internal
source: Internal Mini-SOC detection engine documentation
---

# Internal Detection Rules Reference

This document describes exactly how this system's own deterministic
detection engine works, so the AI analyst can ground its explanations in
the system's actual logic rather than guessing.

## SSH_BRUTE_FORCE
Triggers when a single source IP produces 10 or more `AUTH_FAILURE` events
within a 5-minute window (both thresholds are configurable). Severity: HIGH.
Evidence includes the failure count, the time window, and the usernames
targeted. The same rule covers Windows Security exports: failed logons
(event ID 4625) are normalized to `AUTH_FAILURE` and the alert is then
titled "Windows logon Brute Force" instead of "SSH Brute Force". Maps to
MITRE T1110 (T1110.001 password guessing when one account is targeted,
T1110.003 password spraying when many accounts each receive a few attempts).

## FAILED_THEN_SUCCESS
Triggers when a source IP has 3 or more failed authentication attempts
immediately followed by a successful authentication from the same IP within
the same 5-minute window. Severity: HIGH, or CRITICAL if the failure count
also meets the brute-force threshold (10+). This pattern is a strong
indicator that a brute-force attempt actually succeeded. Applies to both
Linux `auth.log` ("Accepted password") and Windows Security exports (event
ID 4624 after a burst of 4625). Maps to MITRE T1078 (Valid Accounts).

## EXCESSIVE_AUTH_FAILURES
Triggers when a single username accumulates 15 or more failed authentication
attempts within 15 minutes, regardless of source IP. Distinguishing this
from SSH_BRUTE_FORCE: this rule catches credential-stuffing style attacks
distributed across multiple source IPs against one account. Severity:
MEDIUM if from a single IP, HIGH if from multiple IPs.

## SQL_INJECTION
Triggers on HTTP requests whose decoded path/query string matches either
(a) a "strong" SQL injection indicator (UNION SELECT, a quoted tautology
such as `OR '1'='1'`, SLEEP()/BENCHMARK() time-based payloads, or
information_schema references), or (b) two or more "weak" indicators
(stray quotes, SQL comment sequences) together. Severity: HIGH.

## XSS
Triggers on HTTP requests whose decoded path/query string contains
script tags, inline event-handler attributes (onerror=, onload=, ...),
`javascript:` URIs, or references to `document.cookie`/`document.location`.
Severity: MEDIUM.

## PATH_TRAVERSAL
Triggers on HTTP requests containing `../`, `..\\`, or URL-encoded
equivalents (including double-encoded forms). Severity: HIGH.

## SENSITIVE_FILE_ACCESS
Triggers on HTTP requests targeting known-sensitive file paths such as
`/etc/passwd`, `/etc/shadow`, `.env`, `wp-config.php`, `id_rsa`,
`.git/config`, `web.config`, or `.htpasswd`. Severity: HIGH if the HTTP
response status indicates success (2xx), MEDIUM otherwise (the request may
have been blocked).

## Deduplication and correlation
Alerts for the same detection rule and source IP/username are deduplicated
within a rolling window to avoid alert storms. Related alerts (sharing a
source IP, username, or host within a 30-minute window) are grouped into a
single incident by the correlation engine so an analyst investigates one
coherent incident rather than many disconnected alerts.
