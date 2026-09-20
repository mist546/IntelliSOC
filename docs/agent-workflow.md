# Agent Workflow

## Design decision: deterministic tool selection, not LLM function-calling

The project brief asks for an agent that "dynamically chooses relevant
tools" without building "a complicated multi-agent swarm." There are two
common ways to implement "dynamic tool choice":

1. Let the LLM itself decide, via function-calling / a ReAct loop, which
   tools to invoke and in what order.
2. Have deterministic Python code decide which tools are relevant based on
   the alert's actual content (does it have a source IP? a username? is
   there a correlating incident?), and call the LLM only once at the end,
   purely to interpret the assembled evidence.

This project uses **option 2**, implemented in
`backend/app/agents/investigator.py`. This was a deliberate engineering
trade-off, not a shortcut:

- Small local models (this project defaults to a 3-4B parameter class
  model running on CPU) are unreliable at producing well-formed
  function-calling JSON across multiple turns, especially under the
  latency constraints of a live investigation.
- A fixed but *conditional* pipeline (e.g. "only call the threat-intel tool
  if `alert.source_ip` is set") already satisfies "must not blindly call
  every tool" while remaining fully auditable and reproducible - two
  properties the project brief prioritizes explicitly (Correctness >
  golden path > Security > Reliability > Explainability > ... per section 47
  of the spec).
- If a future iteration swaps in a much larger/faster model (e.g. via
  Ollama Cloud), the same tool functions in `app/tools/` can be wrapped in
  a real function-calling loop without changing anything else in the
  pipeline.

## The workflow (implemented in `investigate_alert()`)

1. **Receive alert** - load the alert and its already-linked evidence.
2. **Understand the alert** - detection rule, severity, indicators present.
3. **Determine missing evidence** - which indicators (source_ip, username)
   exist to search on.
4. **Search related logs** - `search_related_logs()` around the alert's
   timestamp (+/- 30 minutes).
5. **Extract indicators** - source IP is the primary pivot for this system.
6. **Threat intelligence enrichment** - only if a source IP is present;
   local provider is always tried, VirusTotal only if configured, and any
   provider failure is caught and skipped rather than raised.
7. **RAG knowledge retrieval** - a query built from the detection rule name
   and alert title, plus a dedicated response-playbook query.
8. **Check previous incidents** - only if a correlating indicator exists.
9. **Aggregate evidence** - everything above is assembled into one
   evidence document with clearly labeled sections.
10. **Calculate risk** - the deterministic risk engine (`services/risk/engine.py`)
    runs regardless of LLM availability.
11. **Send evidence to the local LLM** - a single call, strict system
    prompt (see `services/llm/service.py`), asking for one JSON object.
12. **Validate LLM output** - parsed and validated against the
    `LLMAnalysis` Pydantic schema; malformed output is retried once, then
    reported as a structured failure (never silently ignored, never
    crashes the investigation).
13. **Response recommendation** - taken directly from the validated
    `recommended_actions` field, always paired with
    `requires_human_approval: true`.
14. **Escalation** - currently implicit: CRITICAL/HIGH risk scores and
    `insufficient_evidence: true` are both surfaced prominently in the UI
    for analyst attention; no automatic escalation action is taken.
15. **Investigation result** - a full `Investigation` row is persisted with
    the trace, evidence, threat intel, RAG sources, risk score/factors, and
    AI analysis (or `llm_available: false` + `error_message` if the LLM
    step failed).
16. **Complete** - the alert's status moves from `NEW` to `INVESTIGATING`.

## The trace

Every step above appends a `{step, action, detail}` entry to the
investigation's `trace` list via a small `Trace` helper class. This is
exactly what is shown in the UI as the "agent trace" - concise action
summaries and observations, never a raw model chain-of-thought.

## Tools (`backend/app/tools/`)

| Tool | Called when |
|---|---|
| `get_alert_details` | Always |
| `get_related_events` | Always (events already linked to the alert) |
| `search_related_logs` | Alert has a `source_ip` or `username` |
| `get_ip_threat_intelligence` | Alert has a `source_ip` |
| `get_domain_threat_intelligence` | Available for future domain-based rules |
| `lookup_cve` | Available for future CVE-referencing findings |
| `search_security_knowledge` | Always (grounds the LLM in OWASP/MITRE/CWE/playbooks) |
| `get_response_playbook` | Always (detection-rule-specific playbook query) |
| `search_previous_incidents` | Alert has a `source_ip` or `username` |
| `calculate_risk` | Always |
| `generate_report` | Called separately, from the incident detail page/API, not during investigation |

## Known limitation

The orchestrator's "dynamic tool choice" is rule-based (conditioned on
alert fields), not the LLM freely choosing arbitrary tool call sequences.
This is documented here explicitly per the project's "major failure
protocol" - it is the safest functional design for a small local model,
not a shortfall that was silently mocked.
