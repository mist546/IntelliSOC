"""Knowledge retrieval for investigations and the /api/rag/search endpoint.

Two kinds of matching are combined:
  * exact identifier matching - security knowledge is full of IDs that an
    embedding model treats as near-meaningless tokens (T1110.001, CWE-89,
    CVE-2024-6387, A07:2021, Windows event 4625). Chunks that literally
    contain an ID from the query are included (up to half the result
    slots, most similar first) even below the relevance threshold.
  * semantic (vector) search - everything else, keeping only chunks whose
    cosine similarity reaches RAG_MIN_SCORE, so irrelevant text is never
    handed to the LLM just to fill the top-k.
Results can be restricted to categories (top-level folders) and/or to
specific documents.
"""
import math
import re
from dataclasses import dataclass

from app.config import get_settings
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_query
from app.services.rag.store import IndexMismatchError, check_embedding_signature, collection_count, get_collection
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

WINDOWS_EVENT_IDS = {"1102", "4624", "4625", "4634", "4648", "4672", "4720", "4740", "4768", "4771", "4776"}
# Chunks fetched per identifier before ranking them by similarity.
KEYWORD_CANDIDATES = 50
IDENTIFIER_RE = re.compile(r"\b(T\d{4}(?:\.\d{3})?|CWE-\d{1,4}|CVE-\d{4}-\d{4,7}|A\d{2}:20\d{2}|\d{4})\b", re.IGNORECASE)


@dataclass
class RAGResult:
    content: str
    source: str
    title: str
    category: str
    score: float
    page: int | None = None
    heading: str | None = None
    match: str = "semantic"  # "semantic" or "keyword" (exact identifier)


@dataclass
class RAGSearchResponse:
    available: bool
    results: list[RAGResult]
    message: str = ""


def extract_identifiers(text: str) -> list[str]:
    """Security identifiers worth matching exactly (4-digit numbers only if
    they are Windows Security event IDs)."""
    found: list[str] = []
    for raw in IDENTIFIER_RE.findall(text):
        ident = raw.upper()
        if ident.isdigit() and ident not in WINDOWS_EVENT_IDS:
            continue
        if ident not in found:
            found.append(ident)
    return found


def _where(categories: list[str] | None, sources: list[str] | None) -> dict | None:
    clauses = []
    if categories:
        clauses.append({"category": {"$in": list(categories)}})
    if sources:
        clauses.append({"source": {"$in": list(sources)}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _result(doc: str, meta: dict, score: float, match: str) -> RAGResult:
    return RAGResult(
        content=doc,
        source=meta.get("source", "unknown"),
        title=meta.get("title", "unknown"),
        category=meta.get("category", "general"),
        score=round(score, 4),
        page=meta.get("page"),
        heading=meta.get("heading"),
        match=match,
    )


def search_security_knowledge(
    query: str,
    top_k: int | None = None,
    categories: list[str] | None = None,
    sources: list[str] | None = None,
    min_score: float | None = None,
) -> RAGSearchResponse:
    top_k = top_k or settings.RAG_TOP_K
    min_score = settings.RAG_MIN_SCORE if min_score is None else min_score

    if collection_count() == 0:
        return RAGSearchResponse(
            available=False,
            results=[],
            message="Knowledge base is empty. Run scripts/ingest_knowledge_base.ps1 to index data/knowledge_base.",
        )

    try:
        collection = get_collection()
        check_embedding_signature(collection)
    except IndexMismatchError as exc:
        return RAGSearchResponse(available=False, results=[], message=str(exc))

    try:
        query_embedding = embed_query(query)
    except EmbeddingUnavailableError as exc:
        logger.warning("RAG search unavailable: %s", exc)
        return RAGSearchResponse(
            available=False, results=[], message=f"Embedding model unavailable ({exc}). Knowledge retrieval skipped."
        )

    where = _where(categories, sources)
    results: dict[str, RAGResult] = {}
    try:
        # 1. Exact identifier matches (scored by real similarity for ranking).
        for ident in extract_identifiers(query):
            hits = collection.get(
                where=where, where_document={"$contains": ident}, limit=KEYWORD_CANDIDATES,
                include=["documents", "metadatas", "embeddings"],
            )
            for chunk_id, doc, meta, emb in zip(hits["ids"], hits["documents"], hits["metadatas"], hits["embeddings"]):
                results.setdefault(chunk_id, _result(doc, meta, _cosine(query_embedding, list(emb)), "keyword"))

        # 2. Semantic matches above the relevance threshold.
        raw = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
        for chunk_id, doc, meta, dist in zip(raw["ids"][0], raw["documents"][0], raw["metadatas"][0], raw["distances"][0]):
            score = 1 - dist  # cosine distance -> similarity
            if score >= min_score:
                results.setdefault(chunk_id, _result(doc, meta, score, "semantic"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chroma query failed")
        return RAGSearchResponse(available=False, results=[], message=f"Vector search failed: {exc}")

    # Exact matches get up to half the slots (best first) so they cannot
    # crowd out semantically relevant chunks; leftover slots are backfilled.
    keyword = sorted((r for r in results.values() if r.match == "keyword"), key=lambda r: -r.score)
    semantic = sorted((r for r in results.values() if r.match == "semantic"), key=lambda r: -r.score)
    keyword_slots = (top_k + 1) // 2
    ranked = keyword[:keyword_slots] + semantic
    ranked = (ranked + keyword[keyword_slots:])[:top_k]
    message = "" if ranked else f"No knowledge chunk reached the relevance threshold ({min_score})."
    return RAGSearchResponse(available=True, results=ranked, message=message)
