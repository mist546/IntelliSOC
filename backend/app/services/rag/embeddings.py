import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingUnavailableError(Exception):
    pass


def embed_text(text: str) -> list[float]:
    """Embed text using the local Ollama embedding model.

    Raises EmbeddingUnavailableError on any failure so callers can degrade
    gracefully instead of crashing (Ollama down, model not pulled, timeout).
    """
    try:
        resp = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=settings.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding")
        if not embedding:
            raise EmbeddingUnavailableError("Ollama returned no embedding vector")
        return embedding
    except httpx.HTTPError as exc:
        raise EmbeddingUnavailableError(f"Ollama embedding request failed: {exc}") from exc


EMBED_BATCH_SIZE = 64


def embed_query(query: str) -> list[float]:
    """Embed a search query (with the model's query prefix, see RAG_QUERY_PREFIX)."""
    return embed_text(f"{settings.RAG_QUERY_PREFIX}{query}")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document chunks (with the model's document prefix, see
    RAG_DOC_PREFIX) using Ollama's batch endpoint (/api/embed, Ollama >= 0.3).

    Ingesting a large knowledge base one chunk at a time is dominated by
    per-request overhead; batching 64 chunks per call is ~50x faster on the
    same hardware. Falls back to one-at-a-time if the batch endpoint is not
    available. Raises EmbeddingUnavailableError on failure like embed_text.
    """
    if not texts:
        return []
    texts = [f"{settings.RAG_DOC_PREFIX}{t}" for t in texts]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        try:
            resp = httpx.post(
                f"{settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": settings.OLLAMA_EMBED_MODEL, "input": batch},
                timeout=settings.OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings")
            if not embeddings or len(embeddings) != len(batch):
                raise EmbeddingUnavailableError("Ollama batch embed returned an unexpected number of vectors")
            vectors.extend(embeddings)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:  # older Ollama without /api/embed
                logger.warning("Batch embedding endpoint unavailable; falling back to per-chunk embedding")
                vectors.extend(embed_text(t) for t in batch)
            else:
                raise EmbeddingUnavailableError(f"Ollama batch embedding request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailableError(f"Ollama batch embedding request failed: {exc}") from exc
    return vectors


def is_embedding_available() -> bool:
    try:
        embed_text("healthcheck")
        return True
    except EmbeddingUnavailableError:
        return False
