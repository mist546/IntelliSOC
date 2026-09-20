---
title: Relevant CWE Weakness Classifications
category: cwe
source: MITRE Common Weakness Enumeration (cwe.mitre.org)
---

# Relevant CWE Weakness Classifications

The Common Weakness Enumeration (CWE) is a community-developed list of
software and hardware weakness types.

## CWE-89: SQL Injection
Improper neutralization of special elements used in an SQL command. Occurs
when user-controllable input is concatenated into a SQL query without
parameterization or proper escaping, allowing an attacker to alter the
query's logic (e.g. `' OR '1'='1`), extract data, or in severe cases execute
administrative operations on the database.
**Mitigation**: use parameterized queries / prepared statements or an ORM,
apply least-privilege database accounts, and validate input server-side.

## CWE-79: Cross-Site Scripting (XSS)
Improper neutralization of input during web page generation. User input is
rendered into an HTML response without proper encoding, allowing an
attacker to inject client-side script that executes in a victim's browser
session (e.g. `<script>document.cookie</script>`), enabling session
hijacking or defacement.
**Mitigation**: contextual output encoding, Content-Security-Policy headers,
and input validation.

## CWE-22: Path Traversal
Improper limitation of a pathname to a restricted directory ("Path
Traversal"). Occurs when user-supplied input is used to construct a file
path without sufficient sanitization, allowing sequences like `../` to
escape the intended directory and access arbitrary files on the file
system.
**Mitigation**: canonicalize and validate paths against an allow-list,
avoid passing user input directly into filesystem APIs.

## CWE-307: Improper Restriction of Excessive Authentication Attempts
The software does not implement a sufficient mechanism to prevent multiple
failed authentication attempts within a short time period, making it
susceptible to brute-force attacks.
**Mitigation**: account lockout policies, exponential backoff, CAPTCHA,
rate limiting, and multi-factor authentication.

## CWE-798: Use of Hard-coded Credentials
Software contains hard-coded credentials, such as a password or
cryptographic key, which it uses for its own inbound authentication,
outbound communication, or encryption of internal data. Relevant when
investigating exposed configuration files (e.g. `.env`, `wp-config.php`)
reached via sensitive file access or path traversal.
**Mitigation**: store secrets in a dedicated secrets manager or
environment-based configuration excluded from version control.

## CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
Covers unintentional disclosure of sensitive files, directory listings, or
verbose error messages. Relevant to sensitive file access findings such as
requests for `/etc/passwd` or `.git/config`.
