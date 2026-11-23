# Testing

## Running the backend test suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

101 of the 102 tests are fast (unit/integration against an in-memory SQLite
database and mocked LLM/embedding calls where appropriate) and run in well
under a minute. One test,
`tests/test_investigation_milestone2.py::test_milestone2_agentic_investigation_end_to_end`,
is a **real, unmocked integration test** against your actual local Ollama
instance and the ingested Chroma knowledge base - it is the Milestone 2
mandatory test from the project spec, run for real rather than simulated.
It requires:

- Ollama running (`ollama serve`) with the configured `OLLAMA_MODEL` pulled.
- The knowledge base already ingested (`scripts/ingest_knowledge_base.ps1`).

It takes 30-90+ seconds depending on your hardware (see "LLM latency" in
`docs/setup.md`) and will pass with `llm_available: false` and a populated
`error_message` (rather than fail) if Ollama truly cannot respond in time -
this is intentional graceful-degradation behavior, not a test bug.

The endpoint agent has its own small suite (Windows event XML -> event
mapping), run with the backend's venv because it provides pytest:

```powershell
cd soc-agent
..\backend\.venv\Scripts\python.exe -m pytest tests
```

## What's covered

| File | Covers |
|---|---|
| `test_parsers.py` | auth.log parsing: valid/malformed/empty/missing-IP/missing-username/invalid-timestamp lines; access log, CSV, JSON parsing; Windows Security JSON export parsing (event ID mapping, IP/target-account extraction, PowerShell `/Date()/` timestamps, bad records); format auto-detection |
| `test_detection.py` | 5 failures -> no alert, 10 -> alert, failures+success -> elevated severity, normal login -> no alert, SQLi/XSS/path-traversal/sensitive-file detection, Windows logon failures -> brute force + failed-then-success |
| `test_correlation.py` | related alerts -> one incident; unrelated alerts -> separate incidents |
| `test_golden_path.py` | the Milestone 1 mandatory test (auth.log -> parse -> normalize -> detect -> alert -> correlate -> incident) **and** the full section-37 golden path with the LLM mocked: -> Investigate with AI -> indicator extraction -> related logs -> threat intel -> RAG -> risk -> AI analysis -> auto-generated JSON report -> PDF report download -> dashboard statistics, all via the real HTTP API |
| `test_sample_data_scenarios.py` | the bundled sample logs actually trigger (or don't trigger) the rules they're meant to demonstrate |
| `test_api_auth.py` | registration, login, wrong password, protected-endpoint 401, unauthenticated health check |
| `test_rag_chunker.py` | frontmatter parsing, paragraph-aware chunking, empty-input handling |
| `test_rag_ingestion.py` | ingestion (including subfolders and `.txt`), retrieval, and source metadata against an in-memory Chroma collection with a fast deterministic fake embedding (no Ollama dependency, so it runs in CI) |
| `test_rag_loaders.py` | markdown split by headings (code blocks ignored, heading images/links cleaned), PDFs generated in the test: one section per page with page numbers, running headers/page numbers removed, title from PDF metadata or `_metadata.json`; MITRE STIX bundle -> one section per live technique with mitigations (revoked/deprecated skipped); word-aligned chunk overlap; context headers |
| `test_rag_pipeline.py` | category = folder, context header stored; re-ingestion skips unchanged files, replaces a shrunk file's chunks without leftovers, prunes deleted files; an index from another embedding setup is refused with a `-Reset` message; category filter, relevance threshold, exact-ID keyword match; identifier extraction; query prefix applied; AI citations resolved and invented ones dropped; a chunk shared by two questions shown once in the prompt |
| `test_knowledge_downloader.py` | the knowledge downloader's pure converters on inline fixtures (no network): KEV keyword filter + small-vendor grouping, Sigma YAML -> markdown incl. false positives and invalid input |
| `test_knowledge_api.py` | `GET/POST/DELETE /api/knowledge`: auth required, on-disk vs indexed documents (category = folder), upload sanitises the filename into `custom/`, PDF upload indexed per page, rejects bad extensions / fake PDFs / empty files, saves-but-reports-unindexed when embeddings are unavailable, delete only allowed in `custom/` |
| `test_llm_service.py` | valid JSON, JSON wrapped in extra text, `<think>` blocks stripped, malformed JSON, Ollama unavailable, timeout, missing model, schema-invalid output, severity normalization - all via a fake provider so these run in milliseconds |
| `test_agent_investigator.py` | tool selection is conditional (no source IP -> threat intel tool skipped), evidence gathering populates the trace, investigation completes with LLM unavailable, `insufficient_evidence` is surfaced correctly |
| `test_scanner.py` | SSRF guard rejects unauthorized hosts/schemes, allows localhost, and a real scan against a throwaway local HTTP server finds a missing-CSP-header finding and a sensitive-path finding |
| `test_investigation_milestone2.py` | the real, unmocked Milestone 2 end-to-end test described above |
| `test_live_events.py` | real-time features: the SSE broker delivers messages published from another thread, stream tickets are single-use and required, ingestion publishes `alert.created`/`incident.updated` after commit, agent heartbeat -> `ONLINE` and status ageing (STALE/OFFLINE), `/investigate` returns `RUNNING` and every trace step is published in order, no duplicate run while one is running, a crashing background job ends `FAILED` rather than stuck `RUNNING` |
| `soc-agent/tests/test_windows_collector.py` | Windows Security event XML -> backend event: remote IP kept, local logons attributed to 127.0.0.1, service/system/machine-account logons filtered, lockout without a fake IP, unknown event IDs passed through |

Because `/investigate` runs the agent as a background task, API tests use
the `investigate` fixture in `conftest.py`: it asserts the immediate
`RUNNING` response, then fetches the finished investigation (FastAPI's
TestClient runs background tasks before the request call returns).

## Why most LLM/RAG tests are mocked but one is real

Fully mocking every AI-related test would satisfy the letter of "LLM
tests" and "RAG tests" from the spec but not their intent - a fast, fully
mocked suite could pass even if the actual Ollama/Chroma integration were
broken. This project keeps one genuine end-to-end AI test
(`test_investigation_milestone2.py`) precisely so the Milestone 2 mandatory
test claim is backed by a real run against real local infrastructure, while
keeping the rest of the suite fast and deterministic for everyday
iteration.

## Manual golden-path verification

`scripts/seed_demo_data.ps1` ingests every file in `data/sample_logs/`
directly (no server needed) and creates a demo admin account
(`admin` / `AdminPass123!` - change this password). After seeding, start the
backend and frontend and walk the golden path from the dashboard: Alerts ->
open the SSH brute-force alert -> "Investigate with AI" -> Investigation
detail page -> Incident detail -> Generate Report.
