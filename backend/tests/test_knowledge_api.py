import uuid

import chromadb

from app.api.routes import knowledge as knowledge_route
from app.services.rag import ingest as ingest_module


def _fake_embed_many(texts):
    out = []
    for text in texts:
        vec = [0.0] * 16
        for i, ch in enumerate(text[:64]):
            vec[i % 16] += ord(ch) % 13
        out.append(vec)
    return out


def _isolated_kb(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "bundled.md").write_text("---\ntitle: Bundled Doc\ncategory: playbook\nsource: Test\n---\n\nBundled body text.")
    collection = chromadb.EphemeralClient().get_or_create_collection(name=f"kb_api_test_{uuid.uuid4().hex}")
    monkeypatch.setattr(knowledge_route, "_kb_root", lambda: kb_dir)
    monkeypatch.setattr(knowledge_route, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "get_collection", lambda: collection)
    monkeypatch.setattr(ingest_module, "embed_texts", _fake_embed_many)
    return kb_dir, collection


def test_list_requires_auth(client):
    assert client.get("/api/knowledge").status_code == 401


def test_list_shows_unindexed_and_indexed_documents(client, auth_headers, tmp_path, monkeypatch):
    kb_dir, collection = _isolated_kb(tmp_path, monkeypatch)

    docs = client.get("/api/knowledge", headers=auth_headers).json()
    assert [d["id"] for d in docs] == ["bundled.md"]
    assert docs[0]["indexed"] is False and docs[0]["chunk_count"] == 0
    # Category is the top-level folder; files directly in the root are "general".
    assert docs[0]["title"] == "Bundled Doc" and docs[0]["category"] == "general"
    assert docs[0]["file_type"] == "md" and docs[0]["deletable"] is False

    ingest_module.ingest_knowledge_base(kb_dir=str(kb_dir))
    docs = client.get("/api/knowledge", headers=auth_headers).json()
    assert docs[0]["indexed"] is True and docs[0]["chunk_count"] >= 1


def test_upload_saves_to_custom_folder_and_indexes(client, auth_headers, tmp_path, monkeypatch):
    kb_dir, collection = _isolated_kb(tmp_path, monkeypatch)
    body = "---\ntitle: Our SSH Runbook\ncategory: playbook\nsource: internal wiki\n---\n\nStep 1: rotate credentials."

    resp = client.post(
        "/api/knowledge",
        headers=auth_headers,
        files={"file": ("../../evil name.md", body, "text/markdown")},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] == "custom/evil_name.md"  # path components stripped, spaces sanitised
    assert data["title"] == "Our SSH Runbook" and data["indexed"] is True and data["chunk_count"] >= 1
    assert (kb_dir / "custom" / "evil_name.md").read_text() == body
    assert collection.count() == data["chunk_count"]

    listed = {d["id"]: d for d in client.get("/api/knowledge", headers=auth_headers).json()}
    assert listed["custom/evil_name.md"]["chunk_count"] == data["chunk_count"]


def test_upload_rejects_unsupported_extension_and_empty_file(client, auth_headers, tmp_path, monkeypatch):
    _isolated_kb(tmp_path, monkeypatch)
    bad = client.post("/api/knowledge", headers=auth_headers, files={"file": ("tool.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 400
    fake_pdf = client.post("/api/knowledge", headers=auth_headers, files={"file": ("doc.pdf", b"not a pdf", "application/pdf")})
    assert fake_pdf.status_code == 400
    empty = client.post("/api/knowledge", headers=auth_headers, files={"file": ("doc.md", "   ", "text/markdown")})
    assert empty.status_code == 400


def test_upload_when_embeddings_unavailable_saves_but_reports_not_indexed(client, auth_headers, tmp_path, monkeypatch):
    kb_dir, _ = _isolated_kb(tmp_path, monkeypatch)
    from app.services.rag.embeddings import EmbeddingUnavailableError

    def _down(texts):
        raise EmbeddingUnavailableError("Ollama down")

    monkeypatch.setattr(ingest_module, "embed_texts", _down)
    resp = client.post("/api/knowledge", headers=auth_headers, files={"file": ("notes.txt", "some notes", "text/plain")})
    assert resp.status_code == 201
    assert resp.json()["indexed"] is False and "not indexed" in resp.json()["message"]
    assert (kb_dir / "custom" / "notes.txt").exists()


def test_pdf_upload_is_indexed_per_page_and_can_be_deleted(client, auth_headers, tmp_path, monkeypatch):
    from tests.test_rag_loaders import _make_pdf

    kb_dir, collection = _isolated_kb(tmp_path, monkeypatch)
    pdf_path = tmp_path / "policy.pdf"
    _make_pdf(pdf_path, ["Our escalation policy: call the IT manager first, then the owner, for any confirmed incident."])

    resp = client.post(
        "/api/knowledge", headers=auth_headers, files={"file": ("policy.pdf", pdf_path.read_bytes(), "application/pdf")}
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] == "custom/policy.pdf" and data["file_type"] == "pdf" and data["indexed"] is True
    stored = collection.get(where={"source": "custom/policy.pdf"})
    assert stored["metadatas"][0]["page"] == 1

    deleted = client.delete("/api/knowledge/custom/policy.pdf", headers=auth_headers)
    assert deleted.status_code == 200 and deleted.json()["chunks_removed"] >= 1
    assert not (kb_dir / "custom" / "policy.pdf").exists()
    assert collection.get(where={"source": "custom/policy.pdf"})["ids"] == []


def test_only_custom_documents_can_be_deleted(client, auth_headers, tmp_path, monkeypatch):
    kb_dir, _ = _isolated_kb(tmp_path, monkeypatch)
    assert client.delete("/api/knowledge/bundled.md", headers=auth_headers).status_code == 403
    assert client.delete("/api/knowledge/custom/../bundled.md", headers=auth_headers).status_code in (403, 404)
    assert (kb_dir / "bundled.md").exists()
    assert client.delete("/api/knowledge/custom/missing.md", headers=auth_headers).status_code == 404
