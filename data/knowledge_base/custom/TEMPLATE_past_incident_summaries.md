---
title: Past Incident Summaries - <organisation / lab name>
category: incident-history
source: <who maintains this>
---

# Past incident summaries

<!-- Copy to past_incident_summaries.md. One short paragraph per closed
     incident gives the AI analyst narrative precedent that the database
     search (search_previous_incidents) cannot provide. -->

## <YYYY-MM-DD> - <short title>
What happened: <two or three sentences: alert type, source, target,
outcome>. Root cause: <e.g. password-only SSH exposed on the jump host>.
What worked: <e.g. blocking the /24 at the firewall, resetting the account>.
What we changed: <e.g. key-only auth, fail2ban, MFA on VPN>.
Lessons for similar alerts: <e.g. a burst from this cloud provider's range
was a vulnerability scanner the team had forgotten about>.
