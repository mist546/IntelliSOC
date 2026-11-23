---
title: Response Playbook - Windows Logon Brute Force
category: playbook
source: Internal Mini-SOC playbook (derived from NIST SP 800-61 IR lifecycle and MITRE ATT&CK mitigations M1036, M1032, M1027)
---

# Response Playbook: Windows Logon Brute Force / Password Spraying

Applies to detection rules `SSH_BRUTE_FORCE` (Windows variant, titled
"Windows logon Brute Force"), `FAILED_THEN_SUCCESS` and
`EXCESSIVE_AUTH_FAILURES` when the events come from a Windows Security
export (event IDs 4625 / 4624 / 4740). Maps to MITRE T1110.001 (Password
Guessing), T1110.003 (Password Spraying), T1110.004 (Credential Stuffing)
and, when a logon succeeds, T1078 (Valid Accounts).

## Investigation steps
1. Count the 4625 events per source IP and per target account and note the
   Sub Status codes: many 0xC000006A against one account = guessing; one
   or two per account across many accounts = spraying; 0xC0000064 = the
   attacker is using a wordlist of non-existent names.
2. Note the Logon Type: type 3 (network/SMB/NTLM) or type 10 (RDP) from an
   external address means an exposed service; type 2 means someone at the
   console.
3. Look for a 4624 from the same source IP after the failures, then a
   4672 (special privileges) - together these indicate a successful
   brute force with administrative rights.
4. Look for 4740 lockouts: their presence means lockout policy is working;
   their absence during a long burst suggests spraying below the threshold
   or that lockout policy is not configured.
5. Check the source IP against threat intelligence and against the
   organisation's known-benign sources (VPN egress, vulnerability
   scanners, monitoring systems).
6. Determine whether the targeted accounts are privileged (Administrator,
   Domain Admins, service accounts) or disabled/expired (attempts against
   those indicate an old credential list).
7. If a successful logon occurred, review post-logon activity on the host:
   process creation (4688), new services (7045), new accounts (4720),
   scheduled tasks (4698), and outbound connections.

## Recommended response actions (require human approval before execution)
- Investigate the source IP and cross-reference with threat intelligence;
  consider blocking it at the perimeter firewall or in Windows Firewall.
- Review all successful logons for the targeted accounts in the same
  window and, if compromise is suspected, force a password reset and
  revoke active sessions.
- Enforce or verify an account lockout policy (threshold, duration, reset
  window) - ATT&CK mitigation M1036 Account Use Policies.
- Enable multi-factor authentication for remote access and privileged
  accounts - M1032 Multi-factor Authentication.
- Reduce exposure: do not expose RDP (3389) or SMB (445) to the internet;
  require VPN or a gateway with MFA; enable Network Level Authentication
  for RDP.
- Restrict NTLM where possible and audit NTLM usage; prefer Kerberos.
- Apply a strong password policy and screen for known-breached passwords
  - M1027 Password Policies.
- Ensure "Audit Logon" success and failure auditing is enabled so future
  attempts are visible.
- Escalate to a senior analyst or incident commander if a successful logon
  followed the failures, especially with a 4672 privilege assignment.

## Notes
No destructive or containment action (blocking an IP, disabling an account,
resetting a password) is executed automatically by this system. All actions
above are recommendations for a human analyst to approve and carry out.
