---
title: MITRE ATT&CK Techniques Relevant to This SOC
category: mitre
source: MITRE ATT&CK Framework (attack.mitre.org)
---

# MITRE ATT&CK Techniques Relevant to This SOC

MITRE ATT&CK is a globally-accessible knowledge base of adversary tactics and
techniques based on real-world observations. Below are the techniques most
relevant to the detections this system produces.

## T1110 - Brute Force
Adversaries may use brute force techniques to gain access to accounts when
passwords are unknown or when password hashes are obtained. Sub-techniques
include Password Guessing (T1110.001), Password Cracking (T1110.002),
Password Spraying (T1110.003), and Credential Stuffing (T1110.004).
**Detection guidance**: Monitor authentication logs for multiple failed
login attempts across short time windows, especially from a single source
against a single or multiple accounts. A high volume of failed attempts
followed by a success is a strong indicator of a successful brute-force
compromise. Tactic: Credential Access.

## T1078 - Valid Accounts
Adversaries may obtain and abuse credentials of existing accounts as a means
of gaining initial access, persistence, privilege escalation, or defense
evasion. This is the typical follow-on stage after a successful brute-force
or credential-stuffing attack (T1110): the adversary now operates with a
legitimate, valid account, making detection harder. Tactic: Defense Evasion,
Persistence, Privilege Escalation, Initial Access.

## T1190 - Exploit Public-Facing Application
Adversaries may attempt to exploit a weakness in an Internet-facing
application (web server, API) to gain initial access. SQL injection,
cross-site scripting used for session hijacking, and path traversal
vulnerabilities against public web applications fall under this technique.
Tactic: Initial Access.

## T1005 - Data from Local System
Adversaries search local file systems for files of interest, such as
configuration files or credential stores. Sensitive file access attempts
(e.g. requests for /etc/passwd, /etc/shadow, .env files) are consistent with
reconnaissance for this technique, or with Path Traversal used to reach
those files from a web application context. Tactic: Collection.

## T1595 - Active Scanning
Adversaries may execute active reconnaissance scans to gather information
that can be used during targeting, such as probing a web application with a
range of payloads to discover injection points. A burst of varied malformed
requests (SQLi, XSS, traversal payloads) from the same source in a short
window is consistent with automated vulnerability scanning. Tactic:
Reconnaissance.

## T1548 - Abuse Elevation Control Mechanism
Covers techniques such as abusing `sudo` to execute commands with elevated
privileges. Repeated or unusual `sudo` command usage following a suspicious
login is worth correlating with T1078 and T1110 findings. Tactic: Privilege
Escalation, Defense Evasion.

## Mapping table used by the risk/response engine

| Detection Rule | Primary MITRE Technique | OWASP Category |
|---|---|---|
| SSH_BRUTE_FORCE | T1110 (Brute Force) | A07:2021 |
| FAILED_THEN_SUCCESS | T1110 -> T1078 (Valid Accounts) | A07:2021 |
| EXCESSIVE_AUTH_FAILURES | T1110 (Brute Force) | A07:2021 |
| SQL_INJECTION | T1190 (Exploit Public-Facing Application) | A03:2021 |
| XSS | T1190 (Exploit Public-Facing Application) | A03:2021 |
| PATH_TRAVERSAL | T1190 / T1005 | A01:2021 |
| SENSITIVE_FILE_ACCESS | T1005 (Data from Local System) | A01:2021 |
