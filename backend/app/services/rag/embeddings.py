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


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(t) for t in texts]


def is_embedding_available() -> bool:
    try:
        embed_text("healthcheck")
        return True
    except EmbeddingUnavailableError:
        return False
