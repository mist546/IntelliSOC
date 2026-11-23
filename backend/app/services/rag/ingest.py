"""Index the knowledge base (data/knowledge_base/) into ChromaDB.

Each document is loaded (loaders.py), split into chunks that carry a
context header, embedded and stored with metadata:
    source   path relative to the knowledge base (the document's identity)
    title    document title
    category top-level folder, e.g. response_playbooks, nist, mitre_attack
    page     PDF page number        heading  markdown heading path
    technique_id  ATT&CK ID (STIX)  doc_hash  content hash of the file

Re-running is incremental: unchanged documents (same hash) are skipped, a
changed document's old chunks are replaced (never left behind), and chunks
of documents that were deleted from disk are removed.
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings
from app.services.rag.chunker import chunk_text, context_header
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_texts
from app.services.rag.loaders import METADATA_FILE, UnsupportedDocumentError, load_document
from app.services.rag.store import IndexMismatchError, check_embedding_signature, get_collection
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".json"}
ROOT_CATEGORY = "general"


@dataclass
class IngestSummary:
    documents_processed: int = 0
    documents_unchanged: int = 0
    chunks_indexed: int = 0
    chunks_removed: int = 0
    errors: list[str] = field(default_factory=list)


def list_knowledge_documents(directory: str | Path | None = None) -> list[Path]:
    """All indexable documents under the knowledge base directory, walking
    subfolders. README*, TEMPLATE_* and _-prefixed files (e.g. the
    _metadata.json title files) are documentation, never indexed."""
    root = Path(directory or settings.KNOWLEDGE_BASE_DIR)
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
        and not p.name.upper().startswith(("README", "TEMPLATE_"))
        and not p.name.startswith("_")
    )


def category_for(rel_name: str) -> str:
    """The category is the top-level folder: response_playbooks/escalation.md
    -> response_playbooks. Files directly in the root are 'general'."""
    parts = rel_name.split("/")
    return parts[0] if len(parts) > 1 else ROOT_CATEGORY


def _document_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    meta_file = path.parent / METADATA_FILE
    if meta_file.exists():  # a title change in _metadata.json should re-index too
        try:
            digest.update(json.dumps(json.loads(meta_file.read_text(encoding="utf-8")).get(path.name, {})).encode())
        except (OSError, json.JSONDecodeError):
            pass
    return digest.hexdigest()


def _stored_hash(collection, rel_name: str) -> str | None:
    stored = collection.get(where={"source": rel_name}, include=["metadatas"], limit=1)
    metadatas = stored.get("metadatas") or []
    return metadatas[0].get("doc_hash") if metadatas else None


def remove_document_chunks(rel_name: str, collection=None) -> int:
    collection = collection if collection is not None else get_collection()
    existing = collection.get(where={"source": rel_name}, include=[])
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
    return len(existing["ids"])


def ingest_document(path: Path, root: Path, collection=None, force: bool = False) -> int | None:
    """Chunk, embed and store one document, replacing any chunks it had
    before. Returns the number of chunks indexed, or None if the document is
    unchanged since it was last indexed (skipped). Raises
    EmbeddingUnavailableError if Ollama cannot embed (old chunks are kept)."""
    collection = collection if collection is not None else get_collection()
    check_embedding_signature(collection, stamp_if_empty=True)
    rel_name = path.relative_to(root).as_posix()
    doc_hash = _document_hash(path)
    if not force and _stored_hash(collection, rel_name) == doc_hash:
        return None

    doc = load_document(path)
    category = category_for(rel_name)
    texts, metadatas = [], []
    for section in doc.sections:
        header = context_header(doc.title, section.heading, section.page)
        for chunk in chunk_text(section.text):
            texts.append(f"{header}\n{chunk}")
            meta = {
                "source": rel_name,
                "title": doc.title,
                "category": category,
                "origin": doc.origin,
                "doc_hash": doc_hash,
                "chunk_index": len(metadatas),
                "heading": section.heading,
                "page": section.page,
                **section.extra,
            }
            metadatas.append({k: v for k, v in meta.items() if v is not None})  # Chroma rejects None

    # Embed first: if Ollama fails, the document's previous chunks survive.
    embeddings = embed_texts(texts)
    remove_document_chunks(rel_name, collection)
    if texts:
        collection.add(
            ids=[f"{rel_name}::{i}" for i in range(len(texts))],
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
    logger.info("Indexed %d chunk(s) from %s", len(texts), rel_name)
    return len(texts)


def prune_deleted_documents(root: Path, collection) -> int:
    """Remove chunks whose source document no longer exists on disk."""
    on_disk = {p.relative_to(root).as_posix() for p in list_knowledge_documents(root)}
    stored = collection.get(include=["metadatas"])
    stale_ids = [
        chunk_id for chunk_id, meta in zip(stored["ids"], stored.get("metadatas") or [])
        if meta.get("source") not in on_disk
    ]
    if stale_ids:
        collection.delete(ids=stale_ids)
    return len(stale_ids)


def ingest_knowledge_base(kb_dir: str | None = None, force: bool = False) -> IngestSummary:
    summary = IngestSummary()
    directory = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)

    if not directory.exists():
        summary.errors.append(f"Knowledge base directory not found: {directory}")
        return summary

    doc_files = list_knowledge_documents(directory)
    if not doc_files:
        summary.errors.append(f"No documents ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) found in {directory}")
        return summary

    collection = get_collection()
    try:
        check_embedding_signature(collection, stamp_if_empty=True)
    except IndexMismatchError as exc:
        summary.errors.append(str(exc))
        return summary

    for path in doc_files:
        rel_name = path.relative_to(directory).as_posix()
        try:
            count = ingest_document(path, directory, collection, force=force)
        except (OSError, UnsupportedDocumentError, ValueError) as exc:
            summary.errors.append(f"Could not load {rel_name}: {exc}")
            continue
        except EmbeddingUnavailableError as exc:
            summary.errors.append(f"Embedding failed for {rel_name}: {exc}")
            continue
        if count is None:
            summary.documents_unchanged += 1
        else:
            summary.documents_processed += 1
            summary.chunks_indexed += count

    summary.chunks_removed = prune_deleted_documents(directory, collection)
    return summary
