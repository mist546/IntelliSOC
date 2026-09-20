---
title: Incident Response Lifecycle (NIST SP 800-61 based)
category: reference
source: Adapted from NIST SP 800-61 Rev.2, Computer Security Incident Handling Guide
---

# Incident Response Lifecycle

NIST SP 800-61 describes incident response as a lifecycle with four major
phases. This SOC's workflow (detection -> alert -> correlation -> incident
-> investigation -> report) is designed around this lifecycle.

## 1. Preparation
Establishing the capability to respond, including detection rules, logging,
playbooks, and trained analysts. In this system: the detection engine,
threat intel providers, and knowledge base represent the "preparation"
investments made ahead of time.

## 2. Detection and Analysis
Identifying and validating that an incident has occurred, determining its
scope and impact. In this system: the deterministic detection engine
produces evidence-backed alerts, correlation groups related alerts into
incidents, and the agentic investigation gathers additional evidence
(related logs, threat intelligence, risk scoring) before an AI-assisted
analysis is produced. **Tier-1 analysts should validate AI-generated
analysis against the underlying evidence before acting on it.**

## 3. Containment, Eradication, and Recovery
Limiting damage (containment), removing the root cause (eradication), and
restoring normal operations (recovery). This system deliberately stops
short of this phase: it produces **recommended** containment actions (e.g.
"consider blocking the source IP") but does not execute them automatically.
A human analyst must approve and separately carry out containment actions.

## 4. Post-Incident Activity
Documenting lessons learned, updating detection rules and playbooks based
on what was observed. The generated incident report (JSON/PDF) supports
this phase by capturing the full evidence trail, AI analysis, and response
recommendations for later review.

## Severity guidance used by the risk engine
- **CRITICAL**: strong evidence of successful compromise (e.g. brute-force
  followed by a successful login) combined with corroborating threat
  intelligence or anomaly signals.
- **HIGH**: strong deterministic detection evidence (e.g. brute-force
  threshold met, confirmed injection payload) without confirmed compromise.
- **MEDIUM**: partial or weaker evidence, or activity consistent with
  reconnaissance/scanning rather than confirmed exploitation.
- **LOW**: informational or low-confidence findings that may still warrant
  review but do not indicate likely compromise.
