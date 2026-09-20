---
title: OWASP Top 10 (2021) Summary
category: owasp
source: OWASP Foundation, "OWASP Top 10:2021"
---

# OWASP Top 10 (2021)

The OWASP Top 10 is the industry-standard awareness list of the most critical
security risks to web applications, maintained by the OWASP Foundation.

1. **A01:2021 - Broken Access Control** - Restrictions on what authenticated
   users are allowed to do are not properly enforced, allowing attackers to
   access other users' accounts, view sensitive files, or modify data.

2. **A02:2021 - Cryptographic Failures** - Failures related to cryptography
   (or its absence) that often lead to exposure of sensitive data such as
   passwords, credit card numbers, or health records.

3. **A03:2021 - Injection** - User-supplied data is not validated, filtered,
   or sanitized, allowing hostile data to be interpreted as part of a
   command or query. Includes SQL injection, OS command injection, and LDAP
   injection. Reflected and stored Cross-Site Scripting (XSS) are also
   classified here.

4. **A04:2021 - Insecure Design** - Missing or ineffective control design;
   a broad category representing weaknesses that cannot be fixed by
   implementation alone and require secure-by-design practices.

5. **A05:2021 - Security Misconfiguration** - Missing appropriate security
   hardening, improperly configured permissions, unnecessary features
   enabled, default accounts/passwords unchanged, verbose error messages
   leaking information.

6. **A06:2021 - Vulnerable and Outdated Components** - Using components
   (libraries, frameworks, software modules) with known vulnerabilities or
   that are out of date.

7. **A07:2021 - Identification and Authentication Failures** - Weaknesses in
   authentication mechanisms including permitting brute-force or
   credential-stuffing attacks, weak or default passwords, missing
   multi-factor authentication, and improper session management.

8. **A08:2021 - Software and Data Integrity Failures** - Code and
   infrastructure that does not protect against integrity violations, e.g.
   insecure deserialization, auto-update mechanisms without integrity
   verification, or CI/CD pipelines without proper controls.

9. **A09:2021 - Security Logging and Monitoring Failures** - Insufficient
   logging, detection, monitoring, and active response, allowing breaches to
   go undetected for long periods. This category is the direct motivation
   for building a SOC detection and investigation pipeline like this one.

10. **A10:2021 - Server-Side Request Forgery (SSRF)** - A web application
    fetches a remote resource without validating the user-supplied URL,
    allowing an attacker to coerce the application into sending requests to
    an unexpected destination, including internal-only services.

## Relevance to this system

- **SQL Injection** detections map to **A03:2021 - Injection**.
- **Cross-Site Scripting (XSS)** detections map to **A03:2021 - Injection**.
- **Path Traversal** and **Sensitive File Access** detections map to
  **A01:2021 - Broken Access Control**.
- **SSH Brute Force** and **Failed-Then-Success Login** detections map to
  **A07:2021 - Identification and Authentication Failures**.
- The website security scanner's checks are organized around this same
  Top 10 list.
