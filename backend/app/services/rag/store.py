from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=settings.RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:  # noqa: BLE001
        return 0
