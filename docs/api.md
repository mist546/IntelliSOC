# API Reference

Base URL (local): `http://localhost:8000`. Interactive Swagger UI is always
available at `http://localhost:8000/docs` (FastAPI auto-generated from the
Pydantic schemas - treat this document as a guide, the live `/docs` page as
the source of truth).

All endpoints except `/api/auth/register`, `/api/auth/login`, and
`/api/health` require `Authorization: Bearer <token>`. Agent event ingestion
(`POST /api/events`) instead requires `X-Agent-Id` and `X-Agent-Key` headers.

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | `{username, email, password}`. First user becomes ADMIN, rest ANALYST. |
| POST | `/api/auth/login` | form-urlencoded `username`, `password` (OAuth2 password flow) -> `{access_token, token_type, user}` |
| GET | `/api/auth/me` | current user |

## Logs

| Method | Path | Notes |
|---|---|---|
| POST | `/api/logs/upload` | multipart `file`; validated by extension + size limit; runs full parse -> detect -> correlate pipeline. Format is auto-detected: auth.log, syslog, Apache/Nginx access+error, CSV, JSON, and Windows Security event exports (`Get-WinEvent ... | ConvertTo-Json`) |
| POST | `/api/events` | agent-authenticated; accepts an `{events: [...]}` batch of pre-normalized events |
| GET | `/api/logs` | filters: `source_ip`, `event_type`, `skip`, `limit` |
| GET | `/api/logs/{id}` | single event |

## Alerts

| Method | Path | Notes |
|---|---|---|
| GET | `/api/alerts` | filters: `severity`, `status`, `skip`, `limit` |
| GET | `/api/alerts/{id}` | |
| PATCH | `/api/alerts/{id}/status` | `{status}`, one of NEW/ACKNOWLEDGED/INVESTIGATING/RESOLVED/FALSE_POSITIVE |
| POST | `/api/alerts/{id}/investigate` | starts the agentic investigation **in the background** and returns the `Investigation` immediately with `status: RUNNING`; its `trace` fills in step by step (poll `GET /api/investigations/{id}` or listen on `/api/stream`) until `COMPLETED`/`FAILED`. A second call while one is running returns the running one instead of starting a duplicate. Investigations still running when the backend stops are marked `FAILED` at the next startup |

## Incidents / Investigations

| Method | Path | Notes |
|---|---|---|
| GET | `/api/incidents` | filter: `status` |
| GET | `/api/incidents/{id}` | includes nested `alerts[]` |
| GET | `/api/investigations` | summaries (`id, alert_id, incident_id, status, risk_score, created_at, completed_at`), newest first; query: `status`, `skip`, `limit` (default 100) |
| GET | `/api/investigations/{id}` | full investigation record |
| GET | `/api/investigations/{id}/trace` | just `{id, status, trace}` |

## RAG / Threat Intel

| Method | Path | Notes |
|---|---|---|
| POST | `/api/rag/search` | `{query, top_k, categories?}` -> `{available, message, results[]}`; each result has `content, source, title, category` (top-level folder), `score` (cosine similarity), `page` (PDFs), `heading` (markdown section) and `match` (`semantic`, or `keyword` for an exact ID match such as T1110 / CWE-89 / 4625). Results below `RAG_MIN_SCORE` are omitted |
| GET | `/api/knowledge` | every knowledge base document on disk with its indexed chunk count (`indexed: false` = on disk but not yet embedded), `category` (folder), `file_type` (md/txt/pdf/json) and `deletable` (true only for `custom/`) |
| POST | `/api/knowledge` | multipart `file` (`.md`/`.txt` up to 5 MB, `.pdf` up to 20 MB); saved to `data/knowledge_base/custom/` and indexed immediately (PDFs page by page); 400 for other types, a non-PDF `.pdf`, or a PDF with no extractable text (scanned); 201 with `indexed: false` + `message` if Ollama cannot embed right now |
| DELETE | `/api/knowledge/{id}` | removes an analyst-uploaded document (`custom/...` only, 403 otherwise) and all of its indexed chunks |
| GET | `/api/threat-intel/{indicator}?type=ip\|domain\|hash\|cve` | type auto-detected if omitted |

## Website Scanner

| Method | Path | Notes |
|---|---|---|
| POST | `/api/scans` | `{target_url}`; only `SCAN_ALLOWED_HOSTS` targets permitted (SSRF guard) |
| GET | `/api/scans` | |
| GET | `/api/scans/{id}` | |

## Reports

| Method | Path | Notes |
|---|---|---|
| POST | `/api/reports/{incident_id}` | `{format: "json"\|"pdf"}` |
| GET | `/api/reports/{id}` | metadata + JSON content |
| GET | `/api/reports/{id}/download` | file download (PDF) |

## Agents (log collectors)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/agents/register` | ADMIN only; `{name, hostname}` -> `{id, name, api_key}` (shown once) |
| GET | `/api/agents` | each agent includes `connection_status`: `ONLINE` (seen in the last 90 s), `STALE` (last 10 min), `OFFLINE` or `NEVER_SEEN` |
| DELETE | `/api/agents/{id}` | ADMIN only; removes the agent and revokes its API key. Logs it already shipped are kept (their `agent_id` is cleared). Publishes `agent.deleted` |
| POST | `/api/agents/heartbeat` | agent auth (`X-Agent-Id`/`X-Agent-Key`); updates `last_seen_at`. The endpoint agent calls it every 30 s |

## Live event stream (Server-Sent Events)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/stream/ticket` | JWT auth; returns `{ticket, expires_in}` - a single-use ticket valid for 30 s |
| GET | `/api/stream?ticket=...` | `text/event-stream`. Browsers' `EventSource` cannot send an `Authorization` header, hence the ticket (the JWT never appears in a URL or access log). Each message is `data: {"type", "data", "timestamp"}`; a `: keepalive` comment is sent every 15 s |

Event types: `stream.connected`, `logs.ingested` `{source, count}`,
`alert.created` `{id, title, severity, detection_rule, source_ip, incident_id}`,
`alert.updated` `{id, status}`, `incident.updated` `{id, title, severity}`,
`investigation.started` / `investigation.completed` `{id, alert_id, status}`,
`investigation.step` `{id, alert_id, status, step: {step, action, detail}}`,
`agent.heartbeat` / `agent.deleted` `{id, name}`. Messages are published only after the
change is committed, so a client that refetches on receipt sees it. The
broker is in-process (a single backend process); see
`backend/app/services/live_events.py`.

## Dashboard / Health

| Method | Path | Notes |
|---|---|---|
| GET | `/api/dashboard/statistics` | everything the dashboard page needs in one call |
| GET | `/api/health` | no auth; reports database and LLM reachability (`checks.ollama` probes the local daemon, or checks for an API key when `LLM_PROVIDER=ollama_cloud`) |
| GET | `/api/ai/status` | `{provider, model, embedding_model, reachable}` for the active LLM provider |
