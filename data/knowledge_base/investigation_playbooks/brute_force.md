---
title: Investigation Playbook - Brute Force (SSH and Windows Logon)
source: IntelliSOC investigation playbook (based on NIST SP 800-61r3 and MITRE ATT&CK T1110)
applies_to: SSH_BRUTE_FORCE
identifiers: T1110, T1110.001, 4625, 4740
---

# Investigation Playbook: Brute Force

Use this playbook for `SSH_BRUTE_FORCE` alerts (titled "SSH Brute Force"
or "Windows logon Brute Force"). Goal: decide whether this is a real
attack, whether it succeeded, and how urgent the response is.

## 1. Confirm the volume and time window
- How many failed attempts, over what period? The rule fires at 10+
  failures from one source in 5 minutes; hundreds in minutes indicates an
  automated tool.
- Is the attempt rate constant (machine-like) or irregular (human)?

## 2. Identify the source
- Is the source IP internal (office, VPN range) or external?
- Check the threat intelligence result: a known-malicious or hosting
  provider IP strongly supports an attack.
- Is it a known benign source such as a vulnerability scanner, monitoring
  system or a user's device with a saved old password? Check the
  organisation's list of known benign sources if one exists.
- `127.0.0.1` on Windows means the failures came from this machine itself
  (console, runas, a local program) - look at which program or user.

## 3. Look at the targeted accounts
- Which usernames were tried? Many non-existent names (Linux "invalid
  user", Windows Sub Status 0xC0000064) means a wordlist.
- Were privileged accounts targeted (`root`, `Administrator`, admins,
  service accounts)?
- Windows: was any account locked out (4740)? Lockouts show the policy is
  working; no lockouts during a long burst may mean no lockout policy.

## 4. Check for success - the most important question
- Search the related events for a successful login (`Accepted password`,
  event 4624) from the same source after the failures. If one exists,
  switch to the "Successful Login After Brute Force" playbook and treat
  the account as potentially compromised.
- Check other hosts for logins from the same source in the same period.

## 5. Check history
- Has this source or account appeared in previous incidents?
- Is this part of a larger pattern (several hosts attacked at once)?

## 6. Decide
| Finding | Assessment |
|---|---|
| Known benign source, one account, stops after a password fix | False positive - document and tune |
| External source, failures only, no success | True positive, attack attempt - HIGH, apply brute force response |
| Any success from the attacking source | Possible compromise - CRITICAL, escalate |
| Many hosts or sources involved | Coordinated attack - escalate |

Record in the investigation: source, accounts, count, time window, whether
any login succeeded, and the threat intelligence verdict.
