from dataclasses import dataclass

from app.config import get_settings
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_text
from app.services.rag.store import collection_count, get_collection
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RAGResult:
    content: str
    source: str
    title: str
    category: str
    score: float


@dataclass
class RAGSearchResponse:
    available: bool
    results: list[RAGResult]
    message: str = ""


def search_security_knowledge(query: str, top_k: int | None = None) -> RAGSearchResponse:
    if collection_count() == 0:
        return RAGSearchResponse(
            available=False,
            results=[],
            message=(
                "Knowledge base is empty. Run the ingestion script "
                "(scripts/ingest_knowledge_base.py) to index data/knowledge_base."
            ),
        )

    try:
        query_embedding = embed_text(query)
    except EmbeddingUnavailableError as exc:
        logger.warning("RAG search unavailable: %s", exc)
        return RAGSearchResponse(
            available=False,
            results=[],
            message=f"Embedding model unavailable ({exc}). Knowledge retrieval skipped.",
        )

    try:
        collection = get_collection()
        raw = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k or settings.RAG_TOP_K,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chroma query failed")
        return RAGSearchResponse(available=False, results=[], message=f"Vector search failed: {exc}")

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    results = [
        RAGResult(
            content=doc,
            source=meta.get("source", "unknown"),
            title=meta.get("title", "unknown"),
            category=meta.get("category", "general"),
            score=round(1 - dist, 4),  # cosine distance -> similarity
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
    return RAGSearchResponse(available=True, results=results)
