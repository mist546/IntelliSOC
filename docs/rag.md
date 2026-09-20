# RAG (Retrieval-Augmented Generation)

## Pipeline

```
data/knowledge_base/*.md
        |
Parse frontmatter (title, category, source) + body
        |
Chunk (paragraph-aware, ~800 chars, small overlap)
        |
Embed each chunk (Ollama /api/embeddings, model: nomic-embed-text)
        |
Upsert into ChromaDB (persistent, local, at rag/chroma_db/)
```

Query path:

```
Agent question (e.g. "response playbook for SSH_BRUTE_FORCE")
        |
Embed the question (same Ollama embedding model)
        |
Chroma similarity search (cosine distance, top_k configurable)
        |
Ranked chunks + source metadata (source file, title, category, score)
        |
Included in the LLM's evidence prompt under a labeled KNOWLEDGE section
```

The full knowledge base is **never** dumped into the LLM - only the top-k
retrieved chunks (default 4) for the specific query being asked.

## Why Ollama embeddings instead of sentence-transformers

The project brief asks for a "local embedding model." Rather than adding a
~1-2GB PyTorch + sentence-transformers dependency, this project reuses the
Ollama daemon that is already required for the LLM, via
`ollama pull nomic-embed-text` (274MB). This keeps the install footprint
much smaller and avoids a second ML framework, at the cost of depending on
Ollama also being available for embeddings (if Ollama is down, RAG search
degrades gracefully - see below - it does not crash anything).

## Knowledge base contents (`data/knowledge_base/`)

Eight curated Markdown documents ship with the project, written to be
accurate and consistently structured (frontmatter: `title`, `category`,
`source`) rather than scraped from the web:

- `owasp_top10_2021.md` - OWASP Top 10 (2021) summary, with a mapping table
  from this project's detection rules to OWASP categories.
- `mitre_attack_techniques.md` - the ATT&CK techniques relevant to this
  SOC's detections (T1110, T1078, T1190, T1005, T1595, T1548), with a
  detection-rule -> technique mapping table.
- `cwe_relevant.md` - CWE-89, CWE-79, CWE-22, CWE-307, CWE-798, CWE-200.
- `playbook_ssh_brute_force.md` / `playbook_web_attacks.md` - the response
  playbooks actually used to ground `recommended_actions`.
- `linux_auth_security.md` - how to read auth.log, why volume/timing
  matters, hardening tips.
- `incident_response_lifecycle.md` - NIST SP 800-61-based IR lifecycle and
  the severity guidance the risk engine's bands are based on.
- `internal_detection_rules.md` - documents this project's *own* detection
  engine logic, so the LLM can ground its explanations in the system's
  actual behavior instead of guessing.

## Extending the knowledge base

You are encouraged to add your own documents:

1. Add a new `.md` file to `data/knowledge_base/` with the same frontmatter
   shape (`title`, `category`, `source`).
2. Re-run ingestion: `scripts\ingest_knowledge_base.ps1` (or
   `python backend/scripts/ingest_knowledge_base.py`). Ingestion is
   idempotent per-document (deterministic chunk IDs), so re-running after
   editing a file updates its chunks.

Good candidates to add if you have the source material available: the full
MITRE ATT&CK STIX corpus, NIST SP 800-53 control summaries, or your
organization's actual incident response runbooks. These were intentionally
left out of the default set to keep the bundled knowledge base small,
accurate, and licensing-clean - add what's relevant to your environment.

## Graceful degradation

- **Ollama unreachable during ingestion**: the affected chunk is skipped
  and reported in the ingestion summary's `errors` list; other documents
  still ingest.
- **Ollama unreachable during search**: `search_security_knowledge()`
  returns `available: false` with a clear `message`; the investigation
  continues without RAG evidence rather than failing.
- **Knowledge base never ingested (empty collection)**: search returns
  `available: false` with a message pointing at the ingestion script.

## Testing

`backend/tests/test_rag_chunker.py` and `test_rag_ingestion.py` test
chunking, frontmatter parsing, ingestion, retrieval, and source metadata
using a fast deterministic fake embedding function against an in-memory
Chroma collection (no Ollama required, no network). The real Ollama-backed
path is additionally exercised by the Milestone 2 integration test.
