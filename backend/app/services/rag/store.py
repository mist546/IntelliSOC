from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

settings = get_settings()

# Bump when the chunk format changes (headers, metadata) so an index built by
# an older version is detected and rebuilt rather than silently mixed.
CHUNK_FORMAT_VERSION = 2

# Chroma's HNSW index is approximate. Its defaults (search_ef=10) are too
# narrow for thousands of chunks and measurably missed the best matches, so
# the index is built and searched more thoroughly. Fixed at creation time,
# hence part of the signature below (changing them requires -Reset).
HNSW_SETTINGS = {"hnsw:space": "cosine", "hnsw:construction_ef": 200, "hnsw:search_ef": 100, "hnsw:M": 32}


class IndexMismatchError(Exception):
    """The stored vectors were made with a different embedding setup."""


def embedding_signature() -> str:
    """Everything that determines what a stored vector means. Vectors from
    different models (or prefixes) are not comparable, so mixing them would
    make search silently return nonsense."""
    return (
        f"{settings.OLLAMA_EMBED_MODEL}|doc={settings.RAG_DOC_PREFIX!r}|query={settings.RAG_QUERY_PREFIX!r}"
        f"|chunks=v{CHUNK_FORMAT_VERSION}|hnsw=ef{HNSW_SETTINGS['hnsw:search_ef']}/M{HNSW_SETTINGS['hnsw:M']}"
    )


@lru_cache
def get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection():
    client = get_client()
    # The metadata is only applied when the collection is first created.
    return client.get_or_create_collection(
        name=settings.RAG_COLLECTION_NAME,
        metadata={**HNSW_SETTINGS, "embed_signature": embedding_signature()},
    )


def check_embedding_signature(collection, stamp_if_empty: bool = False) -> None:
    """Raise IndexMismatchError if the collection holds vectors built with a
    different embedding setup. An empty collection is always usable; with
    stamp_if_empty it is labelled with the current signature."""
    expected = embedding_signature()
    stored = (collection.metadata or {}).get("embed_signature")
    if stored == expected:
        return
    if collection.count() == 0:
        if stamp_if_empty:
            # hnsw:space must not be passed to modify() (fixed at creation).
            meta = {k: v for k, v in (collection.metadata or {}).items() if not k.startswith("hnsw:")}
            collection.modify(metadata={**meta, "embed_signature": expected})
        return
    raise IndexMismatchError(
        f"The knowledge base index was built with a different embedding setup "
        f"({stored or 'an older IntelliSOC version'}); current setup is {expected}. "
        "Re-index it with: .\\scripts\\ingest_knowledge_base.ps1 -Reset"
    )


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:  # noqa: BLE001
        return 0


def reset_collection() -> None:
    """Drop and recreate the knowledge base collection (used by
    `ingest_knowledge_base.py --reset`, and required after changing the
    embedding model or prefixes)."""
    client = get_client()
    try:
        client.delete_collection(name=settings.RAG_COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    get_collection()
