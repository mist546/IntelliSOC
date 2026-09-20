---
title: Response Playbook - SSH Brute Force
category: playbook
source: Internal Mini-SOC playbook (derived from NIST SP 800-61 IR lifecycle)
---

# Response Playbook: SSH Brute Force / Credential Access

Applies to detection rules `SSH_BRUTE_FORCE`, `FAILED_THEN_SUCCESS`, and
`EXCESSIVE_AUTH_FAILURES`. Maps to MITRE T1110 (Brute Force) and, when a
successful login follows failures, T1078 (Valid Accounts).

## Investigation steps
1. Confirm the volume and time window of failed attempts and whether they
   originate from one source IP or many (credential stuffing indicator).
2. Determine whether any authentication attempt from the same source IP or
   against the same account succeeded during or shortly after the failure
   burst.
3. If a successful login occurred, review all post-authentication activity
   for that session: commands executed, files accessed, new sessions
   opened, privilege escalation (`sudo`) usage.
4. Check the source IP against available threat intelligence.
5. Check whether the targeted account is a privileged or service account.

## Recommended response actions (require human approval before execution)
- Investigate the source IP and cross-reference with threat intelligence.
- Review all successful login activity for the account and time window.
- Review post-authentication activity for signs of compromise (new users,
  cron jobs, outbound connections, modified files).
- Consider a credential reset for the targeted account(s).
- Enable or review multi-factor authentication for the affected account(s).
- Consider blocking the source IP at the firewall or SSH configuration
  (e.g. fail2ban, security group rule).
- Escalate to a senior analyst or incident commander if compromise is
  confirmed or strongly suspected.

## Notes
No destructive or containment action (blocking an IP, disabling an account)
is executed automatically by this system. All actions above are
recommendations for a human analyst to approve and carry out.
