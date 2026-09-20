from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.services.rag.chunker import chunk_text, parse_markdown_document
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_text
from app.services.rag.store import get_collection
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class IngestSummary:
    documents_processed: int = 0
    chunks_indexed: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def ingest_knowledge_base(kb_dir: str | None = None) -> IngestSummary:
    summary = IngestSummary()
    directory = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)

    if not directory.exists():
        summary.errors.append(f"Knowledge base directory not found: {directory}")
        return summary

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        summary.errors.append(f"No markdown documents found in {directory}")
        return summary

    collection = get_collection()

    for path in md_files:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            summary.errors.append(f"Could not read {path.name}: {exc}")
            continue

        meta, body = parse_markdown_document(raw)
        chunks = chunk_text(body)
        summary.documents_processed += 1

        ids, embeddings, documents, metadatas = [], [], [], []
        for idx, chunk in enumerate(chunks):
            try:
                embedding = embed_text(chunk)
            except EmbeddingUnavailableError as exc:
                summary.errors.append(f"Embedding failed for {path.name} chunk {idx}: {exc}")
                continue
            ids.append(f"{path.stem}::{idx}")
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append(
                {
                    "source": path.name,
                    "title": meta.get("title", path.stem),
                    "category": meta.get("category", "general"),
                    "origin": meta.get("source", "unknown"),
                    "chunk_index": idx,
                }
            )

        if ids:
            collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
            summary.chunks_indexed += len(ids)
            logger.info("Indexed %d chunk(s) from %s", len(ids), path.name)

    return summary
