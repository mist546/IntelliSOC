import chromadb

from app.services.rag import ingest as ingest_module
from app.services.rag import service as service_module


def _fake_embed(text: str) -> list[float]:
    # Deterministic, fast, offline embedding stand-in: a small fixed-size
    # vector derived from character codes, good enough to exercise the
    # ingestion/retrieval pipeline without depending on a running Ollama.
    vec = [0.0] * 16
    for i, ch in enumerate(text[:64]):
        vec[i % 16] += ord(ch) % 13
    return vec


def test_ingestion_and_retrieval_with_source_metadata(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "doc1.md").write_text(
        "---\ntitle: SSH Guidance\ncategory: playbook\nsource: Test Source\n---\n\n"
        "This document explains SSH brute force response steps in detail for the test."
    )

    ephemeral_client = chromadb.EphemeralClient()
    collection = ephemeral_client.get_or_create_collection(name="test_kb")

    monkeypatch.setattr(ingest_module, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "embed_text", _fake_embed)
    monkeypatch.setattr(service_module, "get_collection", lambda: collection)
    monkeypatch.setattr(service_module, "collection_count", lambda: collection.count())
    monkeypatch.setattr(service_module, "embed_text", _fake_embed)

    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.documents_processed == 1
    assert summary.chunks_indexed >= 1
    assert summary.errors == []

    response = service_module.search_security_knowledge("SSH brute force response", top_k=3)
    assert response.available is True
    assert len(response.results) >= 1
    assert response.results[0].source == "doc1.md"
    assert response.results[0].title == "SSH Guidance"
    assert response.results[0].category == "playbook"


def test_search_reports_unavailable_when_knowledge_base_empty(monkeypatch):
    ephemeral_client = chromadb.EphemeralClient()
    empty_collection = ephemeral_client.get_or_create_collection(name="empty_kb")

    monkeypatch.setattr(service_module, "get_collection", lambda: empty_collection)
    monkeypatch.setattr(service_module, "collection_count", lambda: empty_collection.count())

    response = service_module.search_security_knowledge("anything")
    assert response.available is False
    assert response.results == []
    assert "ingest" in response.message.lower() or "empty" in response.message.lower()
