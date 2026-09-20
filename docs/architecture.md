# Architecture

## Overview

Mini-SOC is a small, layered Security Operations Center pipeline. Every
stage is deterministic and evidence-producing until the very end, where a
local LLM is used strictly to *explain and summarize* evidence that has
already been gathered by deterministic code - never to independently decide
whether something is an attack.

```
Security Logs (upload or agent)
        |
Ingestion (validate, size/type limits)
        |
Parsing (format-specific: auth.log, syslog, Apache/Nginx, CSV, JSON)
        |
Normalization (-> common LogEvent model)
        |
Detection Engine (deterministic rules, produces evidence)
        |
Alert (severity, confidence, evidence[])
        |
Correlation (groups related alerts by time/IP/user/host)
        |
Incident
        |
Agentic Investigation (orchestrator, section below)
        |
Report (JSON/PDF) -> SOC Dashboard
```

## Backend layout (`backend/app/`)

```
main.py              FastAPI app, router wiring, startup/lifespan
config.py            Pydantic settings, all env-configurable values
models/               SQLAlchemy ORM models (User, Agent, LogEvent, Alert,
                       Incident, Investigation, ThreatIntel, WebsiteScan, Report)
schemas/               Pydantic request/response schemas
api/routes/             Thin FastAPI routers - no business logic here
services/
  parsing/               Format-specific line/record parsers -> ParsedEvent
  normalization/          ParsedEvent -> LogEvent ORM row
  detection/              One module per rule family + engine.py orchestrator
  correlation/            Alert -> Incident grouping
  ingestion/               Ties parsing+normalization+detection+correlation
                            together for both file upload and agent event intake
  threat_intel/            Provider interface + Local/VirusTotal/NVD providers
  rag/                     Chunking, embeddings (Ollama), Chroma store, ingest/query
  llm/                     Ollama local/cloud providers + structured-output service
  risk/                    Deterministic risk engine + supplementary ML anomaly detector
  scanning/                OWASP-focused website scanner (SSRF-guarded)
  reporting/               Report content builder + PDF renderer
agents/investigator.py  The ONE agentic investigation orchestrator
tools/                   Individual tool functions the orchestrator calls
```

## Why one orchestrator, not a multi-agent swarm

The project brief explicitly scopes this down to "ONE investigation
orchestrator" (not a complex multi-agent system). `app/agents/investigator.py`
implements this: given an alert, it *dynamically* decides which tools are
relevant (e.g. it only looks up IP threat intelligence if the alert has a
source IP; it never calls every tool unconditionally) and builds an
auditable, numbered trace of what it did. See `docs/agent-workflow.md` for
the full design rationale, including why tool selection is done in Python
rather than via LLM function-calling.

## Evidence provenance

The system is careful to keep four categories of information visually and
structurally distinct, both internally and in the LLM prompt/response:

- **EVIDENCE** - directly observed log data (ground truth).
- **THREAT_INTELLIGENCE** - output of configured TI providers.
- **KNOWLEDGE** - chunks retrieved from the RAG knowledge base.
- **INFERENCE** - the LLM's own conclusions, clearly labeled as AI analysis
  and always marked `requires_human_approval: true`.

## Database

SQLite is used by default for zero-setup local development
(`data/mini_soc.db`), but all models use portable SQLAlchemy types (String,
DateTime, Float, JSON) with no SQLite-specific features, so switching
`DATABASE_URL` to a PostgreSQL connection string works without model
changes (see `docs/setup.md`).

## Frontend

React + Vite + TypeScript + Tailwind CSS, talking to the backend purely
over the REST API described in `docs/api.md`, authenticating with a JWT
bearer token stored client-side.

## Security boundaries

- Uploaded log files are only ever read as text and pattern-matched; they
  are never executed or evaluated.
- The website scanner refuses any target outside an explicit allow-list
  (`SCAN_ALLOWED_HOSTS`) and resolves hostnames to reject private/internal
  IPs, to prevent SSRF.
- The LLM never executes shell commands, and every "recommended" response
  action is explicitly distinguished from an "executed" one - this system
  performs no automatic containment.
