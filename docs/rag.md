# RAG (Retrieval-Augmented Generation)

The investigator grounds its analysis in a local knowledge base: playbooks,
MITRE ATT&CK, NIST and OWASP guidance, CWE and CVE data. This document
describes how documents are indexed, how they are retrieved for an alert,
how the AI's use of them is checked, and how retrieval quality is measured.
The knowledge base layout itself is described in
[`data/knowledge_base/README.md`](../data/knowledge_base/README.md).

## Pipeline

```
data/knowledge_base/**  (.md .txt .pdf, MITRE STIX .json)
   -> loaders.py        split into sections (markdown headings / PDF pages / ATT&CK techniques)
   -> chunker.py        ~800-character chunks, word-aligned overlap, context header per chunk
   -> embeddings.py     nomic-embed-text via Ollama, "search_document: " prefix, batches of 64
   -> ChromaDB          cosine HNSW index (search_ef 100), metadata: source, title, category (= folder), page,
                        heading, technique_id, doc_hash
investigation
   -> rule_knowledge.py detection rule -> its investigation/response playbooks + ATT&CK/CWE IDs
   -> service.py        exact identifier match + semantic search above RAG_MIN_SCORE
   -> investigator.py   numbered [K1..Kn] knowledge in the prompt; the LLM must cite K ids;
                        citations are verified and unknown ones dropped
```

Code: `backend/app/services/rag/` (`loaders.py`, `chunker.py`,
`embeddings.py`, `store.py`, `ingest.py`, `service.py`, `rule_knowledge.py`)
and `backend/app/tools/knowledge_tools.py`.

## Indexing

- **Sections before chunks.** Markdown is split on headings, so a chunk
  knows its section; PDFs are split per page (page numbers are kept for
  citations, running headers/footers and page-number lines are removed,
  hyphenated line breaks are re-joined); the MITRE STIX bundle becomes one
  section per live technique/sub-technique with its tactics, platforms,
  detection notes and the names of its mitigations (revoked/deprecated
  objects are skipped).
- **Context header.** Every stored chunk starts with e.g.
  `[NIST SP 800-61 Rev. 3 | p. 14]` or `[Brute Force Response > Containment]`,
  so the embedding, the LLM and the analyst all see where it came from.
- **Category = top-level folder** (`response_playbooks`, `nist`, ...),
  which is what retrieval filters on.
- **Incremental.** Each chunk stores a SHA-256 hash of its file. Re-running
  ingestion skips unchanged files, replaces all chunks of a changed file
  (a shorter file never leaves stale chunks behind), and deletes chunks of
  files removed from disk. New vectors are computed before old ones are
  deleted, so an Ollama failure never loses a document's existing chunks.
- **Embedding guard.** The collection records the embedding model, the
  prefixes, the chunk format version and the HNSW index settings. Vectors from a different setup
  are not comparable, so both ingestion and search refuse a mismatched
  index with a message to run `ingest_knowledge_base.ps1 -Reset`.
- **Task prefixes.** `nomic-embed-text` is trained with
  `search_document: ` / `search_query: ` prefixes (config
  `RAG_DOC_PREFIX` / `RAG_QUERY_PREFIX`; set both empty for a model that
  does not use them, then re-index).

Measured on this knowledge base: 87 documents -> 7,091 chunks in about 2
minutes on a laptop CPU; a re-run with nothing changed takes 1.5 s.

## Retrieval for an investigation

The investigator asks three separate questions, each answered from its own
part of the knowledge base, and records each as a trace step:

| Question | Tool | Searches |
|---|---|---|
| How do I verify this alert? | `get_investigation_playbook` | the rule's investigation playbooks |
| What should be recommended? | `get_response_playbook` | the rule's response playbooks (+ escalation) |
| What is this attack? | `get_background_knowledge` | the rule's attack/vulnerability docs, then `attack_knowledge`, `vulnerability_knowledge`, `mitre_attack`, `owasp`, `nist` (+ `windows`, `hardening` for auth alerts) |

- The rule-to-document map (`rule_knowledge.py`) makes sure the right
  playbook is always consulted; semantic search then picks the most
  relevant sections inside it. If none of a rule's mapped documents exist,
  the tool falls back to a relevance search over the whole playbook folder.
- The query is built from the rule's plain-language topic, its ATT&CK/CWE/
  OWASP identifiers and the alert text **with IP addresses removed** (they
  carry no meaning for retrieval).
- **Exact identifier matching.** Embedding models treat IDs such as
  `T1110.003`, `CWE-89`, `CVE-2024-6387`, `A07:2021` or Windows event
  `4625` as near-meaningless tokens, so chunks that literally contain an ID
  from the query are added (up to half the result slots, ranked by
  similarity), even below the threshold.
- **Relevance threshold.** Other chunks must reach `RAG_MIN_SCORE` (cosine
  similarity, default 0.65), so irrelevant text is never handed to the
  LLM just to fill the top-k. The value was calibrated with the evaluation
  below: correct chunks scored >= 0.747, while unrelated queries ("chocolate
  cake recipe", "football score") top out at 0.51-0.60.
- A chunk that answers two questions is shown once in the prompt and
  referenced from the second section ("Also relevant here: [K1]").

## Citations and grounding

Every knowledge chunk in the prompt is numbered `[K1]`..`[Kn]` with its
source and page. The system prompt requires the LLM to list the ids it
relied on in `references`. After the response is validated, each id is
resolved against what was actually provided; ids that were never provided
are dropped (and counted in the "AI citations checked" trace step), so the
UI and reports can only show sources that really exist. The investigation
page highlights cited chunks and lists "Sources cited by the AI" with page
numbers; the JSON and PDF reports include them too.

## Evaluation

`backend/scripts/evaluate_rag.py` runs the 26 queries in
`backend/scripts/rag_eval_set.json` (each with the document, folder or
ATT&CK technique that should be found) against the real index:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\evaluate_rag.py            # add --verbose for the top 5 per query
```

Result on the current knowledge base (nomic-embed-text, top-k 4):

| Metric | Value |
|---|---|
| hit@1 (right document ranked first) | 81% (21/26) |
| hit@4 (right document among the 4 given to the LLM) | 100% (26/26) |
| MRR (mean reciprocal rank) | 0.897 |

The five queries not ranked first were each beaten by a closely related,
also-relevant document, by a similarity margin of 0.001-0.013: the OWASP
Top 10 A03 Injection chapter ahead of the injection prevention cheat
sheets; NIST SP 800-92 p. 41 ahead of the OWASP Logging Cheat Sheet; the
MITRE ATT&CK entries T1556.006 and T1110.004 ahead of the OWASP MFA and
Credential Stuffing cheat sheets; and two Mozilla OpenSSH guideline
sections ahead of the CISA KEV list for "actively exploited OpenSSH
vulnerabilities" (rank 3).

**Finding from the evaluation - approximate search.** ChromaDB's HNSW
index is approximate. With its default search breadth (`search_ef` = 10)
an otherwise identical rebuild of the index dropped hit@4 to 96%: exact
similarity showed the CISA KEV chunks at 0.747 while the index returned
NVD chunks at 0.734. The collection is therefore created with
`search_ef` 100, `construction_ef` 200 and `M` 32 (`store.py`,
`HNSW_SETTINGS`); after rebuilding, the KEV chunk was returned at its
exact similarity (0.747) and hit@4 was back to 100%. These settings are part of the
index signature, so an index built with the old defaults is detected and
must be rebuilt with `-Reset`.

## Why Ollama embeddings instead of sentence-transformers

The project reuses the Ollama daemon already required for the LLM
(`ollama pull nomic-embed-text`, 274 MB) rather than adding a 1-2 GB
PyTorch + sentence-transformers dependency. The cost is that embeddings
depend on Ollama being available, which is handled gracefully (below).

## Graceful degradation

- **Ollama unreachable during ingestion**: the affected document is
  reported in the summary's errors and keeps its previous chunks; other
  documents still ingest. A UI upload in that state is saved but reported
  as not indexed.
- **Ollama unreachable, empty index, or mismatched index during search**:
  retrieval returns `available: false` with a clear message; the
  investigation records it in the trace and continues without knowledge
  evidence.

## Testing

Fast tests (fake embeddings, in-memory Chroma, no Ollama):
`test_rag_loaders.py` (markdown sections, PDF pages generated in the test,
header removal, STIX techniques and mitigations, chunking), `test_rag_pipeline.py`
(folder categories, incremental re-ingestion, stale-chunk removal, pruning,
embedding guard, category filter, threshold, exact-ID match, prefixes,
citation checking, shared chunks in the prompt), `test_rag_ingestion.py`,
`test_knowledge_api.py` (including PDF upload and delete). The real
Ollama path is exercised by `test_investigation_milestone2.py` and by
`evaluate_rag.py`.
