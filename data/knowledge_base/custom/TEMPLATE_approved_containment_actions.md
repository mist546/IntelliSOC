---
title: Approved Containment Actions - <organisation / lab name>
category: policy
source: <who maintains this>
---

# Approved containment actions

<!-- Copy to approved_containment_actions.md and fill in. This system never
     executes containment automatically; this document tells the AI analyst
     which recommendations an analyst may act on alone and which need
     sign-off, so requires_human_approval guidance is specific to you. -->

## Tier-1 analyst may perform without further approval
- Block a single external source IP at <firewall / WAF> for up to <N> hours.
- Force a password reset for a non-privileged user account.
- Increase logging verbosity on the affected host.

## Requires Tier-2 / SOC lead approval
- Disable or lock any account.
- Block an IP range or a country.
- Isolate a host from the network.
- Terminate processes or services on production systems.

## Requires incident commander approval
- Any action on domain controllers, identity providers or backups.
- Any action affecting customer-facing availability.
- Engaging law enforcement or external responders.

## Never
- <e.g. wiping or reimaging a host before forensics are captured>
