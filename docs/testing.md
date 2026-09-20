# Testing

## Running the backend test suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

54 of the 55 tests are fast (unit/integration against an in-memory SQLite
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

## What's covered

| File | Covers |
|---|---|
| `test_parsers.py` | auth.log parsing: valid/malformed/empty/missing-IP/missing-username/invalid-timestamp lines; access log, CSV, JSON parsing; format auto-detection |
| `test_detection.py` | 5 failures -> no alert, 10 -> alert, failures+success -> elevated severity, normal login -> no alert, SQLi/XSS/path-traversal/sensitive-file detection |
| `test_correlation.py` | related alerts -> one incident; unrelated alerts -> separate incidents |
| `test_golden_path.py` | the Milestone 1 mandatory test: auth.log -> parse -> normalize -> detect -> alert -> correlate -> incident, via the real HTTP API |
| `test_sample_data_scenarios.py` | the bundled sample logs actually trigger (or don't trigger) the rules they're meant to demonstrate |
| `test_api_auth.py` | registration, login, wrong password, protected-endpoint 401, unauthenticated health check |
| `test_rag_chunker.py` | frontmatter parsing, paragraph-aware chunking, empty-input handling |
| `test_rag_ingestion.py` | ingestion, retrieval, and source metadata against an in-memory Chroma collection with a fast deterministic fake embedding (no Ollama dependency, so it runs in CI) |
| `test_llm_service.py` | valid JSON, JSON wrapped in extra text, `<think>` blocks stripped, malformed JSON, Ollama unavailable, timeout, missing model, schema-invalid output, severity normalization - all via a fake provider so these run in milliseconds |
| `test_agent_investigator.py` | tool selection is conditional (no source IP -> threat intel tool skipped), evidence gathering populates the trace, investigation completes with LLM unavailable, `insufficient_evidence` is surfaced correctly |
| `test_scanner.py` | SSRF guard rejects unauthorized hosts/schemes, allows localhost, and a real scan against a throwaway local HTTP server finds a missing-CSP-header finding and a sensitive-path finding |
| `test_investigation_milestone2.py` | the real, unmocked Milestone 2 end-to-end test described above |

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
