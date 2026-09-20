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
| POST | `/api/logs/upload` | multipart `file`; validated by extension + size limit; runs full parse -> detect -> correlate pipeline |
| POST | `/api/events` | agent-authenticated; accepts an `{events: [...]}` batch of pre-normalized events |
| GET | `/api/logs` | filters: `source_ip`, `event_type`, `skip`, `limit` |
| GET | `/api/logs/{id}` | single event |

## Alerts

| Method | Path | Notes |
|---|---|---|
| GET | `/api/alerts` | filters: `severity`, `status`, `skip`, `limit` |
| GET | `/api/alerts/{id}` | |
| PATCH | `/api/alerts/{id}/status` | `{status}`, one of NEW/ACKNOWLEDGED/INVESTIGATING/RESOLVED/FALSE_POSITIVE |
| POST | `/api/alerts/{id}/investigate` | runs the full agentic investigation synchronously (can take 20-90s+ depending on hardware); returns the `Investigation` |

## Incidents / Investigations

| Method | Path | Notes |
|---|---|---|
| GET | `/api/incidents` | filter: `status` |
| GET | `/api/incidents/{id}` | includes nested `alerts[]` |
| GET | `/api/investigations/{id}` | full investigation record |
| GET | `/api/investigations/{id}/trace` | just `{id, status, trace}` |

## RAG / Threat Intel

| Method | Path | Notes |
|---|---|---|
| POST | `/api/rag/search` | `{query, top_k}` -> `{available, message, results[]}` |
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
| GET | `/api/agents` | |

## Dashboard / Health

| Method | Path | Notes |
|---|---|---|
| GET | `/api/dashboard/statistics` | everything the dashboard page needs in one call |
| GET | `/api/health` | no auth; reports database and Ollama reachability |
