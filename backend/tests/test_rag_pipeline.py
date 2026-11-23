"""Incremental ingestion, the embedding-setup guard, retrieval (filters,
relevance threshold, exact identifiers) and AI citation checking - all with
an in-memory Chroma collection and fake embeddings (no Ollama needed)."""
import uuid

import chromadb
import pytest

from app.agents.investigator import resolve_references
from app.services.rag import embeddings as embeddings_module
from app.services.rag import ingest as ingest_module
from app.services.rag import service as service_module
from app.services.rag.store import IndexMismatchError, check_embedding_signature


def _embed(text: str) -> list[float]:
    # Bag-of-keywords vector: texts sharing these words are similar.
    words = ["brute", "force", "password", "sql", "injection", "xss", "script", "traversal", "file", "incident"]
    lowered = text.lower()
    return [1.0 + lowered.count(w) for w in words]


@pytest.fixture()
def kb(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    (kb_dir / "response_playbooks").mkdir(parents=True)
    (kb_dir / "attack_knowledge").mkdir()
    (kb_dir / "response_playbooks" / "brute.md").write_text(
        "---\ntitle: Brute Force Response\n---\n\n# Containment\n\nBlock the brute force source and reset the password."
    )
    (kb_dir / "attack_knowledge" / "sqli.md").write_text(
        "---\ntitle: SQL Injection\n---\n\nSQL injection (CWE-89) abuses sql queries built from input."
    )
    collection = chromadb.EphemeralClient().get_or_create_collection(name=f"kb_{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"})
    monkeypatch.setattr(ingest_module, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "embed_texts", lambda texts: [_embed(t) for t in texts])
    monkeypatch.setattr(service_module, "get_collection", lambda: collection)
    monkeypatch.setattr(service_module, "collection_count", lambda: collection.count())
    monkeypatch.setattr(service_module, "embed_query", _embed)
    return kb_dir, collection


def test_chunks_carry_folder_category_and_context_header(kb):
    kb_dir, collection = kb
    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.documents_processed == 2 and summary.errors == []
    stored = collection.get(where={"source": "response_playbooks/brute.md"})
    assert stored["metadatas"][0]["category"] == "response_playbooks"
    assert stored["metadatas"][0]["heading"] == "Containment"
    assert stored["documents"][0].startswith("[Brute Force Response > Containment]\n")


def test_reingest_skips_unchanged_replaces_changed_and_prunes_deleted(kb):
    kb_dir, collection = kb
    long_doc = kb_dir / "attack_knowledge" / "long.md"
    long_doc.write_text("---\ntitle: Long\n---\n\n" + "\n\n".join(f"Paragraph {i} about incident handling. " * 12 for i in range(6)))
    ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    before = len(collection.get(where={"source": "attack_knowledge/long.md"})["ids"])
    assert before > 1

    second = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert second.documents_unchanged == 3 and second.documents_processed == 0

    long_doc.write_text("---\ntitle: Long\n---\n\nNow a single short paragraph.")  # shrinks
    ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert len(collection.get(where={"source": "attack_knowledge/long.md"})["ids"]) == 1  # no stale chunks

    (kb_dir / "attack_knowledge" / "sqli.md").unlink()
    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.chunks_removed >= 1
    assert collection.get(where={"source": "attack_knowledge/sqli.md"})["ids"] == []


def test_index_built_with_other_embedding_setup_is_refused(kb):
    kb_dir, collection = kb
    ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    collection.modify(metadata={"embed_signature": "some-other-model|..."})
    with pytest.raises(IndexMismatchError):
        check_embedding_signature(collection)
    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.errors and "-Reset" in summary.errors[0]
    response = service_module.search_security_knowledge("brute force")
    assert response.available is False and "-Reset" in response.message


def test_category_filter_threshold_and_exact_identifier_match(kb):
    kb_dir, _ = kb
    ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))

    only_playbooks = service_module.search_security_knowledge("brute force password", categories=["response_playbooks"], min_score=0)
    assert {r.category for r in only_playbooks.results} == {"response_playbooks"}

    nothing = service_module.search_security_knowledge("brute force password", min_score=0.9999)
    assert nothing.available is True and nothing.results == [] and "threshold" in nothing.message

    by_id = service_module.search_security_knowledge("weakness CWE-89", min_score=0.9999)
    assert [(r.source, r.match) for r in by_id.results] == [("attack_knowledge/sqli.md", "keyword")]


def test_identifier_extraction():
    ids = service_module.extract_identifiers("T1110.001 and t1078, CWE-89, CVE-2024-6387, A07:2021, event 4625, port 2222")
    assert ids == ["T1110.001", "T1078", "CWE-89", "CVE-2024-6387", "A07:2021", "4625"]  # 2222 is not an event ID


def test_embedding_prefixes_are_applied(monkeypatch):
    sent = []
    monkeypatch.setattr(embeddings_module, "embed_text", lambda text: sent.append(text) or [0.0])
    embeddings_module.embed_query("brute force")
    assert sent == ["search_query: brute force"]


def test_ai_citations_are_resolved_and_invented_ones_dropped():
    knowledge = [
        {"id": "K1", "source": "response_playbooks/brute.md", "title": "Brute", "page": None, "heading": "Containment", "category": "response_playbooks"},
        {"id": "K2", "source": "nist/sp_800_61_rev3.pdf", "title": "NIST", "page": 14, "heading": None, "category": "nist"},
    ]
    resolved, unknown = resolve_references(["K2", "[k1]", "K9", "K2"], knowledge)
    assert [r["id"] for r in resolved] == ["K2", "K1"]
    assert resolved[0]["page"] == 14
    assert unknown == ["K9"]


def test_knowledge_shared_by_two_questions_is_shown_once_and_referenced():
    from types import SimpleNamespace

    from app.agents.investigator import _build_evidence_prompt

    knowledge = [
        {"id": "K1", "source": "response_playbooks/web_attack_response.md", "content": "Inspect the endpoint.",
         "purpose": "investigation_playbook", "also": ["response_playbook"]},
    ]
    risk = SimpleNamespace(risk_score=70, severity="HIGH", confidence=0.8, risk_factors=[])
    prompt = _build_evidence_prompt({}, [], [], knowledge, [], risk)
    response_section = prompt.split("### RESPONSE_PLAYBOOK")[1].split("### BACKGROUND")[0]
    assert prompt.count("Inspect the endpoint.") == 1
    assert "Also relevant here: [K1] (shown above)." in response_section
    assert "No response playbook retrieved" not in response_section
