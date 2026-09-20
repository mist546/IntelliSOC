# Mini-SOC

**An Agentic AI-Based Mini-SOC for Automated Tier-1 Security Alert Triage,
Investigation, Threat Intelligence Enrichment, and Response Recommendation
using Local LLMs and RAG.**

A small, working, locally runnable Security Operations Center built as a
university final-year project. It ingests security logs, deterministically
detects common attack patterns, correlates related alerts into incidents,
and then runs an agentic investigation that enriches evidence with threat
intelligence and a RAG-backed security knowledge base before asking a local
LLM (via Ollama) to produce a structured, human-reviewable analysis and
response recommendation - never an automatic action.

## Why this exists

Tier-1 SOC analysts spend a large share of their time on repetitive
triage: is this alert real, what else happened around it, is this IP
known-bad, what does the playbook say to do. This project automates that
repetitive first pass while keeping a human analyst firmly in control -
the system recommends, it never autonomously contains, blocks, or disables
anything.

## Architecture

```
Logs -> Ingestion -> Parsing -> Normalization -> Detection -> Alert
      -> Correlation -> Incident -> Agentic Investigation
      -> (Related evidence + Threat Intel + RAG knowledge + Risk score)
      -> Local LLM analysis -> Response recommendation -> Report -> Dashboard
```

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown,
[`docs/agent-workflow.md`](docs/agent-workflow.md) for how the agentic
investigation is designed (and why it's deterministic tool-selection rather
than free-form LLM function-calling), and [`docs/rag.md`](docs/rag.md) for
the knowledge base pipeline.

## Features

- **Log ingestion**: file upload (auth.log, syslog, Apache/Nginx access &
  error logs, CSV, JSON) or a lightweight Python endpoint agent that tails
  files and streams normalized events.
- **Deterministic detection engine**: SSH brute force, failed-then-success
  login, excessive auth failures, SQL injection, XSS, path traversal,
  sensitive file access - every alert carries explicit evidence.
- **Correlation**: related alerts (same IP/user/host within a time window)
  are grouped into one incident.
- **Agentic investigation**: one orchestrator that gathers related logs,
  threat intelligence, and RAG knowledge, computes a transparent risk
  score, and asks a local LLM for a structured, schema-validated analysis
  with an auditable step-by-step trace.
- **Threat intelligence**: a mandatory offline/local provider (works with
  no internet access) plus optional VirusTotal and NVD integrations.
- **RAG knowledge base**: OWASP Top 10, MITRE ATT&CK, CWE, response
  playbooks, incident response lifecycle, and this project's own detection
  rules - chunked, embedded via Ollama, and retrieved via ChromaDB.
- **Risk engine**: deterministic, transparent scoring with an itemized
  factor list; a supplementary Isolation Forest anomaly detector never
  independently declares an attack.
- **Website security scanner**: safe, SSRF-guarded, OWASP-focused passive
  checks against explicitly authorized lab targets only.
- **Reporting**: JSON and PDF incident reports with the full evidence
  trail, AI analysis, and risk assessment - always distinguishing
  *recommended* from *executed* actions.
- **Dark SOC dashboard**: React/TypeScript frontend covering every stage
  of the pipeline.

## Technology stack

| Layer | Tech |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn |
| Database | SQLite (default, zero-setup) / PostgreSQL-compatible |
| Frontend | React, Vite, TypeScript, Tailwind CSS, recharts |
| AI | Ollama (local or cloud), ChromaDB, nomic-embed-text |
| ML | scikit-learn (Isolation Forest, supplementary only) |
| Deployment | Docker Compose, or fully local without Docker |

## Quickstart

```powershell
# 1. Pull the required Ollama models (see docs/setup.md for details)
ollama pull gemma4:latest
ollama pull nomic-embed-text

# 2. Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
copy .env.example .env

# 3. Ingest the knowledge base and seed demo data
.\scripts\ingest_knowledge_base.ps1
.\scripts\seed_demo_data.ps1

# 4. Run it
.\scripts\start_backend.ps1      # http://localhost:8000  (in one terminal)
.\scripts\start_frontend.ps1     # http://localhost:5173  (in another terminal)
```

Log in with the seeded demo account: `admin` / `AdminPass123!` (change this
password, or register your own account instead - the first registered user
automatically becomes an admin).

Full step-by-step instructions, PostgreSQL setup, the endpoint agent, and
Docker usage are in [`docs/setup.md`](docs/setup.md).

## Demo workflow (golden path)

1. Go to **Logs**, upload `data/sample_logs/auth_brute_force.log` (or it's
   already been ingested by `seed_demo_data.ps1`).
2. Go to **Alerts** - see the `SSH_BRUTE_FORCE` (HIGH) and
   `FAILED_THEN_SUCCESS` (CRITICAL) alerts, both linked to one incident.
3. Open the brute-force alert, click **Investigate with AI**. This gathers
   related logs, threat intelligence (the sample IP `203.0.113.55` is
   marked malicious in the bundled local threat intel data), RAG knowledge,
   and a risk score, then asks the local LLM for a structured analysis.
   Takes roughly 30-90 seconds depending on your hardware.
4. Review the investigation: the numbered trace, evidence, threat intel,
   knowledge sources, risk factors, and AI-recommended actions (clearly
   marked as requiring human approval).
5. Open the **Incident**, click **Generate Report** (JSON or PDF).
6. Check the **Dashboard** for the aggregate view.

## Project structure

```
mini-soc/
├── backend/            FastAPI application (see docs/architecture.md)
├── soc-agent/          Lightweight Python log-tailing collector agent
├── frontend/           React + Vite + TypeScript dashboard
├── data/
│   ├── sample_logs/       Synthetic demo logs (SSH brute force, web attacks, normal traffic)
│   ├── knowledge_base/    RAG source documents (OWASP/MITRE/CWE/playbooks)
│   └── threat_intel/      Local/offline threat intelligence data
├── rag/chroma_db/      Persistent vector store (created by the ingestion script)
├── scripts/            PowerShell convenience scripts
├── docs/                Architecture, setup, API, agent workflow, RAG, testing docs
├── docker-compose.yml
└── .env.example
```

## Known limitations

- **LLM latency is hardware-dependent.** On CPU-only hardware, a full
  investigation's LLM call can take 30-90+ seconds. The system is designed
  to degrade gracefully (the investigation still completes with all
  non-LLM evidence) rather than fail if this exceeds the configured
  timeout. If you have an Ollama account, switching `OLLAMA_MODEL` to a
  `:cloud`-suffixed model (e.g. `gpt-oss:120b-cloud`) cuts this to ~5-15
  seconds with zero code changes - verified with a real end-to-end run;
  see "Using Ollama Cloud" in `docs/setup.md`.
- **The agent's "dynamic tool selection" is rule-based**, not free-form LLM
  function-calling - a deliberate reliability trade-off for small local
  models, explained in `docs/agent-workflow.md`.
- **Docker Compose has not been build-tested** in this project's
  development environment (no running Docker daemon available at the
  time); the configuration was written carefully to handle the
  backend-image path assumptions correctly, but please validate
  `docker compose up --build` yourself. The local (non-Docker) setup is
  fully tested and is the current recommended path.
- **The website scanner performs safe, passive OWASP-oriented checks only**
  against an explicit allow-list of hosts (SSRF-guarded) - it is not a
  penetration-testing tool.
- **PostgreSQL support is schema-compatible but not integration-tested**
  in this environment (only SQLite was available); all models use portable
  SQLAlchemy types with no SQLite-specific features.

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/setup.md`](docs/setup.md)
- [`docs/api.md`](docs/api.md)
- [`docs/agent-workflow.md`](docs/agent-workflow.md)
- [`docs/rag.md`](docs/rag.md)
- [`docs/testing.md`](docs/testing.md)

## Security notes

Passwords are hashed with bcrypt; API access uses JWT bearer tokens;
endpoint agents authenticate with per-agent credentials (never
hard-coded); uploaded files are validated by extension/size and only ever
read as text, never executed; the website scanner is SSRF-guarded and
authorized-targets-only; the LLM never executes shell commands and every
response recommendation is explicitly distinguished from an executed
action - no destructive or containment action is ever taken automatically.

## Changelog

- **Milestone 1** - Core SOC: project foundation, auth, log ingestion,
  parsing (auth.log/syslog/Apache/Nginx/CSV/JSON), normalization,
  deterministic detection engine (7 rules), alert correlation, incidents.
- **Milestone 2** - AI SOC Engine: RAG knowledge base + ChromaDB + Ollama
  embeddings, local/cloud Ollama LLM service with structured output
  validation, threat intelligence providers (local/VirusTotal/NVD), risk
  engine + supplementary Isolation Forest anomaly detector, the agentic
  investigation orchestrator with an auditable trace.
- **Milestone 3** - Complete application: OWASP-focused website scanner,
  JSON/PDF reporting, full API surface, complete React dashboard (all
  pages).
- **Milestone 4** - Finalization: soc-agent endpoint collector, expanded
  sample data (web attacks, normal traffic), Docker Compose, full test
  suite (55 tests including a real, unmocked end-to-end Ollama
  integration test), complete documentation set.
