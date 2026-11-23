---
title: Escalation Policy - <organisation / lab name>
category: policy
source: <who maintains this>
---

# Escalation policy

<!-- Copy to escalation_policy.md and fill in. Tells the AI analyst what
     "escalate" concretely means here so recommendations are actionable. -->

## Severity levels and response targets
- CRITICAL (confirmed compromise, privileged account, internet-facing
  critical asset): notify <role / on-call rota> within <N> minutes via
  <channel>; incident commander is <role>.
- HIGH (strong indicators, no confirmed compromise): assign to a Tier-2
  analyst within <N> hours; update the incident every <N> hours.
- MEDIUM / LOW: handled by Tier-1 within the working day; batch-review
  weekly.

## Who to contact
- SOC lead: <name / role>, <channel>
- System owners: see asset_context.md
- Out of hours: <procedure>

## When to escalate immediately regardless of severity
- A successful logon followed a brute-force burst on a privileged account.
- Evidence of data exfiltration or destructive activity.
- Threat intelligence marks the source as a known malicious infrastructure.
