# IntelliSOC

**An Agentic AI-Based IntelliSOC for Automated Tier-1 Security Alert Triage,
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
  error logs, CSV, JSON, Windows Security event exports) or a lightweight
  Python endpoint agent that tails log files **and reads the live Windows
  Security event log**, streaming normalized events every 2 s with a
  heartbeat so the dashboard shows each agent as online/stale/offline.
- **Wazuh integration**: collect from other machines with Wazuh agents - a
  bridge on the Wazuh manager forwards `alerts.json` to IntelliSOC, which
  maps SSH, Windows logon and web events onto its own detection rules
  (setup: `docs/setup.md`, "Collecting logs with Wazuh"). No VMs needed
  for a demo: `lab\start_lab.ps1 -Wazuh` runs a Wazuh manager and agent in
  Docker alongside the attack lab.
- **Real-time dashboard**: a Server-Sent Events stream pushes new alerts,
  incidents, ingested logs and investigation progress to every open
  browser within about a second; HIGH/CRITICAL alerts pop up as toasts.
- **Attack simulator** for live demos: plays an SSH brute force out in
  real time, or makes real failed Windows logons so Windows itself writes
  the 4625 events the agent then collects.
- **Deterministic detection engine**: SSH brute force, failed-then-success
  login, excessive auth failures, SQL injection, XSS, path traversal,
  sensitive file access - every alert carries explicit evidence.
- **Correlation**: related alerts (same IP/user/host within a time window)
  are grouped into one incident.
- **Agentic investigation**: one orchestrator that gathers related logs,
  threat intelligence, and RAG knowledge, computes a transparent risk
  score, and asks a local LLM for a structured, schema-validated analysis
  with an auditable step-by-step trace. It runs in the background and the
  analyst watches each step appear live.
- **Threat intelligence**: a mandatory offline/local provider (works with
  no internet access) plus optional VirusTotal and NVD integrations.
- **RAG knowledge base**: investigation and response playbooks, MITRE
  ATT&CK (full STIX dataset), NIST PDFs (SP 800-61r3, CSF 2.0, SP 800-92,
  cited by page), OWASP, CWE, exploited/recent CVEs and this project's own
  detection rules, organised by purpose in folders. For every alert the
  agent asks three questions (how to verify it, what to recommend, what
  the attack is), combines exact ID matching (T1110, CWE-89, event 4625)
  with semantic search above a calibrated relevance threshold, and must
  cite the sources it used - citations are checked. Measured retrieval:
  right document in the top 4 for 26/26 evaluation queries. Analysts can
  upload their own `.md`/`.txt`/`.pdf` documents from the UI.
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

# 3. Pull the public reference material into the knowledge base (~60 MB):
#    MITRE ATT&CK, NIST PDFs, OWASP, CWE, CISA KEV, recent NVD CVEs
.\scripts\download_knowledge_base.ps1 -All

# 4. Ingest the knowledge base and seed demo data
.\scripts\ingest_knowledge_base.ps1
.\scripts\seed_demo_data.ps1

# 5. Run it
.\scripts\start_backend.ps1      # http://localhost:8000  (in one terminal)
.\scripts\start_frontend.ps1     # http://localhost:5173  (in another terminal)
```

Keep `OLLAMA_BASE_URL` at `http://127.0.0.1:11434` (the default) rather than
`localhost` - on Windows the `localhost` form costs ~2 s per Ollama request
(IPv6-first resolution); see `docs/setup.md`.

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
3. Open the brute-force alert, click **Investigate with AI**. The
   investigation page opens at once and its timeline fills in live as the
   agent gathers related logs, threat intelligence (the sample IP
   `203.0.113.55` is marked malicious in the bundled local threat intel
   data), RAG knowledge and a risk score, then asks the local LLM for a
   structured analysis (roughly 10-90 seconds depending on your hardware).
   You can navigate away; a toast says when it finishes.
4. Review the investigation: the numbered trace (indicators extracted,
   "11 failed attempts found", "successful login detected", threat intel,
   RAG, risk, LLM, recommendation, report), evidence, threat intel,
   knowledge sources, risk factors, and AI-recommended actions (clearly
   marked as requiring human approval).
5. Open the **Incident** - a JSON report was already generated by the agent
   as its final step; click **Generate Report** for a PDF.
6. Check the **Dashboard** for the aggregate view.
7. Optional Windows variant: upload
   `data/sample_logs/windows_security_events.json` (a `Get-WinEvent` export
   with 12 failed logons and one success from the same IP) - the same
   brute-force and failed-then-success rules fire, titled "Windows logon
   Brute Force".
8. Optional: on **Knowledge Base**, add your own `.md` runbook - it is
   indexed immediately and cited by later investigations.

## Live demo (real-time)

1. Start the backend and frontend, and open the **Dashboard** (the top bar
   shows **Live** when the event stream is connected).
2. Register an agent on the **Agents** page, then start it in a terminal
   (Run as Administrator if you also want the live Windows Security log):
   ```powershell
   cd soc-agent
   $env:MINISOC_AGENT_ID="<id>"; $env:MINISOC_AGENT_KEY="<api_key>"
   .\.venv\Scripts\python.exe agent.py
   ```
   The agent shows as **ONLINE** within seconds.
3. In another terminal: `.\scripts\simulate_attack.ps1`. Failed SSH
   logins from `203.0.113.55` are written ~1.5 s apart; shortly after the
   10th, a HIGH brute-force toast appears, then a CRITICAL
   "Successful Login After Failed Attempts" - no page refresh needed.
   Use `--ip random` for repeat runs.
4. With the agent elevated, `.\scripts\simulate_attack.ps1 --scenario
   windows-logon` makes real failed logons against this PC, for an
   account that doesn't exist; the resulting genuine 4625 events raise
   "Windows logon Brute Force from 127.0.0.1". Typing a wrong password at
   `runas /user:%COMPUTERNAME%\someuser cmd` ten times works too.

Details: `docs/setup.md` section 4.

## Project structure

```
mini-soc/
├── backend/            FastAPI application (see docs/architecture.md)
├── soc-agent/          Lightweight Python log-tailing collector agent
├── frontend/           React + Vite + TypeScript dashboard
├── data/
│   ├── sample_logs/       Synthetic demo logs (SSH brute force, web attacks, normal traffic)
│   ├── knowledge_base/    RAG documents, one folder per purpose (playbooks, attack knowledge,
│   │                      mitre_attack, nist PDFs, owasp, ...; see its README)
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
- **The live event stream is in-process.** It is a simple broker inside
  the single backend process (how this project runs). Running several
  backend worker processes would need an external broker such as Redis
  pub/sub, otherwise each browser only sees events from the worker it is
  connected to.
- **Live Windows Security log collection needs an elevated agent**, and
  the Windows logon scenario of the simulator relies on the default
  "Audit Logon: Failure" policy being on. Both were built and unit-tested,
  and `wevtutil` bookmarking was verified live against the System log, but
  the end-to-end Security-log path was not run during development because
  no elevated terminal was available - please verify it on your machine.
- **Several hand-written knowledge documents are still missing.** The
  knowledge base structure is complete, but only two of the planned
  attack-knowledge / investigation-playbook documents exist, the response
  playbooks are the three original ones (no `compromised_account.md` or
  `escalation.md` yet) and the four `vulnerability_knowledge/*.md` guides
  are not written. The investigator falls back to searching the whole
  playbook folder, and the missing files are listed in
  `data/knowledge_base/README.md`.
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
- **Post-milestone hardening (knowledge base, Windows logs, golden path)**:
  - Knowledge base downloader (`scripts/download_knowledge_base.ps1`) for
    OWASP Cheat Sheets, MITRE ATT&CK Enterprise (STIX), the CWE catalogue,
    NIST SP 800-61 r2/r3 (PDF -> text) and recent NVD CVEs; ingestion now
    walks subfolders, accepts `.txt`, embeds in batches of 64 (~3,000
    chunks in ~45 s instead of ~100 min) and has a `-Reset` option.
  - `GET/POST /api/knowledge` + Knowledge Base page upload: analysts add
    their own `.md`/`.txt` runbooks, indexed immediately.
  - Windows Security event log support (JSON exports from `Get-WinEvent`):
    event-ID mapping, IP/target-account extraction, and the brute-force /
    failed-then-success rules now cover Windows logons; bundled sample.
  - Agent trace now records "Indicators extracted", "Failed authentication
    attempts found" and "Successful login detected" observations, feeds
    them to the LLM ahead of the truncated event sample, and finishes with
    a `generate_report` tool call that persists a JSON incident report.
  - Full section-37 golden-path integration test (upload -> ... -> AI ->
    report -> dashboard) with the LLM mocked, plus Windows and knowledge
    API tests (76 tests total).
  - Ollama default URL switched to `127.0.0.1` (Windows `localhost` = IPv6
    first = ~2 s penalty per request).
- **Knowledge base expansion (recommended sources)**: five more download
  sources - CISA KEV (actively exploited CVEs), OWASP Top 10 full chapters,
  OWASP WSTG chapters, Mozilla OpenSSH guideline, Sigma rules with false
  positives - plus ATT&CK sub-techniques for the auth tactics and every
  ATT&CK mitigation, nine more cheat sheets, NIST SP 800-123 and wider NVD
  keywords (99 documents / ~5,000 chunks, 85 s ingest). Two new bundled
  docs (`windows_logon_events.md`, `playbook_windows_brute_force.md`) so
  Windows investigations cite logon types and NTSTATUS codes, and five
  `TEMPLATE_*` files in `custom/` for organisation-specific context.
  `data/knowledge_base/README.md` explains every source, the templates and
  what not to add.
- **Real-time SOC**:
  - Live event stream: `GET /api/stream` (Server-Sent Events, authenticated
    with a single-use ticket from `POST /api/stream/ticket`). Ingestion,
    alert status changes, investigations and agent heartbeats publish
    events after commit; the frontend refreshes the affected data
    instantly, toasts HIGH/CRITICAL alerts and shows a Live indicator.
  - Investigations run in the background: `/investigate` returns
    `RUNNING` immediately, every trace step is saved and streamed as it
    happens (live timeline on the investigation page), duplicate clicks
    reuse the running investigation, and runs interrupted by a restart are
    marked `FAILED` at startup.
  - Endpoint agent: live Windows Security event log collection via
    `wevtutil` with a persistent bookmark and noise filtering, heartbeat
    every 30 s (`POST /api/agents/heartbeat`; Agents page shows
    ONLINE/STALE/OFFLINE), 2 s polling, and syslog timestamps are now read
    as host local time.
  - `soc-agent/simulate_attack.py` (+ `scripts/simulate_attack.ps1`): live
    SSH brute-force playback and real failed Windows logons.
  - Backend started with `--timeout-graceful-shutdown 3` so open live
    connections cannot stall a restart or `--reload`.
  - 9 new backend tests (`test_live_events.py`) and 6 agent tests
    (`soc-agent/tests`); 85 backend tests at that point.
- **RAG rebuild (knowledge base restructure)**:
  - Knowledge base reorganised into purpose folders (`attack_knowledge/`,
    `investigation_playbooks/`, `response_playbooks/`,
    `vulnerability_knowledge/`, `mitre_attack/`, `nist/`, `owasp/`, ...);
    category = folder. The downloader writes straight into this layout;
    the withdrawn NIST SP 800-61r2 and the old text conversions are gone.
  - Native PDF ingestion, page by page with page numbers kept for
    citations (running headers/footers removed); PDFs can be uploaded from
    the UI. The raw MITRE ATT&CK STIX JSON is ingested directly (697
    techniques/sub-techniques with mitigations).
  - Incremental, safe ingestion: content hashes skip unchanged files,
    changed files never leave stale chunks, deleted files are pruned, and
    an index built with a different embedding setup is refused.
  - Retrieval: nomic-embed-text task prefixes, heading/page context in
    every chunk, exact identifier matching, a calibrated relevance
    threshold (0.65), wider HNSW search after the evaluation showed the
    default missed best matches.
  - Investigation: separate investigation-playbook / response-playbook /
    background knowledge steps driven by a rule-to-document map; numbered
    [K] knowledge with verified AI citations shown in the UI and reports.
  - `DELETE /api/knowledge/{id}` for analyst uploads; `scripts/evaluate_rag.py`
    (26 queries: hit@4 100%, hit@1 81%, MRR 0.897).
  - Fixed `scripts/ingest_knowledge_base.ps1`, which contained a stray
    control character and could not find the backend folder.
  - New tests: `test_rag_loaders.py`, `test_rag_pipeline.py` and PDF upload/delete API
    tests; 102 backend tests in total (101 fast + the real-Ollama test).
- **Run-time fixes**:
  - Pinned `posthog<6` in `backend/requirements.txt`. chromadb 0.5.23 calls
    the pre-6.0 `posthog.capture()` signature, so with posthog 7.x every
    RAG/Chroma call logged `Failed to send telemetry event ... capture()
    takes 1 positional argument` errors (harmless but floods the backend
    terminal). Existing installs: `.\backend\.venv\Scripts\python.exe -m pip
    install "posthog<6"`.
  - Added `.vscode/settings.json` pointing VS Code at `backend/.venv`
    (instead of the empty root `.venv`) so imports resolve and the Problems
    panel stops reporting every package as missing; fixed the Chrome launch
    config to open the Vite port 5173 instead of 8080.
- **Wazuh in Docker**:
  - `lab\start_lab.ps1 -Wazuh`: the attack lab gains a Wazuh 4.14.10
    manager container (official image without Filebeat, no indexer) and
    the target runs a Wazuh agent. The manager writes every event to
    `archives.json` (`logall_json`), bind-mounted to
    `data/live_logs/wazuh/`, which the soc-agent's default config tails -
    so IntelliSOC sees every log line, not only Wazuh's alerts. The two lab
    modes are exclusive, so nothing is reported twice. Verified end to end
    with real hydra/curl attacks: all six lab detections fire, ~5 s from
    request to IntelliSOC event.
  - Fixed the Wazuh parser against real manager output: a frequency rule
    (5763 brute force, 40112 success-after-failures) carries a log line
    that appears nowhere else, so it is now parsed instead of being
    discarded as a duplicate - before, `FAILED_THEN_SUCCESS` could never
    fire from Wazuh data. Archive lines without a `rule` are accepted.
    The hand-written `wazuh_alerts.json` sample no longer contains the
    duplicate line real Wazuh never writes; `wazuh_archives.json` is a
    real archive recorded from the lab.
  - The lab's nginx access log is now `nginx_access.log`.
