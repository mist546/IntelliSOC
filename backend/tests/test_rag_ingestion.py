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
    (kb_dir / "response_playbooks").mkdir()
    (kb_dir / "response_playbooks" / "doc1.md").write_text(
        "---\ntitle: SSH Guidance\nsource: Test Source\n---\n\n"
        "This document explains SSH brute force response steps in detail for the test."
    )

    ephemeral_client = chromadb.EphemeralClient()
    collection = ephemeral_client.get_or_create_collection(name="test_kb", metadata={"hnsw:space": "cosine"})

    monkeypatch.setattr(ingest_module, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "embed_texts", lambda texts: [_fake_embed(t) for t in texts])
    monkeypatch.setattr(service_module, "get_collection", lambda: collection)
    monkeypatch.setattr(service_module, "collection_count", lambda: collection.count())
    monkeypatch.setattr(service_module, "embed_query", _fake_embed)

    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.documents_processed == 1
    assert summary.chunks_indexed >= 1
    assert summary.errors == []

    response = service_module.search_security_knowledge("SSH brute force response", top_k=3)
    assert response.available is True
    assert len(response.results) >= 1
    assert response.results[0].source == "response_playbooks/doc1.md"
    assert response.results[0].title == "SSH Guidance"
    assert response.results[0].category == "response_playbooks"  # the folder


def test_search_reports_unavailable_when_knowledge_base_empty(monkeypatch):
    ephemeral_client = chromadb.EphemeralClient()
    empty_collection = ephemeral_client.get_or_create_collection(name="empty_kb")

    monkeypatch.setattr(service_module, "get_collection", lambda: empty_collection)
    monkeypatch.setattr(service_module, "collection_count", lambda: empty_collection.count())

    response = service_module.search_security_knowledge("anything")
    assert response.available is False
    assert response.results == []
    assert "ingest" in response.message.lower() or "empty" in response.message.lower()


def test_ingestion_walks_subfolders_and_accepts_txt(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    (kb_dir / "downloaded" / "owasp").mkdir(parents=True)
    (kb_dir / "top.md").write_text("---\ntitle: Top\n---\n\nTop-level markdown document about SQL injection.")
    (kb_dir / "downloaded" / "owasp" / "nested.md").write_text("---\ntitle: Nested\n---\n\nNested markdown about XSS.")
    (kb_dir / "downloaded" / "nist.txt").write_text("Plain text extracted from a NIST PDF about incident handling.")
    (kb_dir / "README.md").write_text("# not indexed")
    (kb_dir / "downloaded" / "TEMPLATE_asset_context.md").write_text("---\ntitle: T\n---\n\n<placeholder> not indexed")

    ephemeral_client = chromadb.EphemeralClient()
    collection = ephemeral_client.get_or_create_collection(name="test_kb_nested")
    monkeypatch.setattr(ingest_module, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "embed_texts", lambda texts: [_fake_embed(t) for t in texts])

    summary = ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    assert summary.documents_processed == 3
    assert summary.errors == []

    stored = collection.get()
    sources = {m["source"] for m in stored["metadatas"]}
    assert sources == {"top.md", "downloaded/owasp/nested.md", "downloaded/nist.txt"}
    assert all("::" in i for i in stored["ids"])
