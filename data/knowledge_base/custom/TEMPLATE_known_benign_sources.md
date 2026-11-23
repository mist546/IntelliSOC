---
title: Known Benign Sources - <organisation / lab name>
category: reference
source: <who maintains this>
---

# Known benign sources

<!-- Copy to known_benign_sources.md and fill in. The single biggest
     false-positive reducer: vulnerability scanners, monitoring probes and
     VPN egress addresses routinely trigger brute-force and web-attack
     rules. Describe them so the AI analyst can weigh "insufficient
     evidence" correctly. This does NOT suppress detection - alerts still
     fire; the analyst just gets the context. -->

## Vulnerability scanners
- <scanner name>, source IP(s) <ip>, scans <targets> every <schedule>.
  Expect: many 4xx web requests with injection-like payloads, SSH banner
  grabs, sensitive-path probes. Contact: <team>.

## Monitoring / health checks
- <tool>, source IP(s) <ip>: HTTP GET /health every <interval>.

## VPN / NAT egress
- <ip range>: shared egress for <N> staff; many users appear as one IP,
  so failed-login counts from it are not one attacker.

## CI / automation accounts
- <account name>: logs in from <ip> at <times>; failures usually mean an
  expired token, not an attack.
