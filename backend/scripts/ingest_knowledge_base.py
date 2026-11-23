"""Ingest data/knowledge_base/ (.md, .txt, .pdf, MITRE STIX .json) into ChromaDB.

Incremental: unchanged documents are skipped, changed ones re-indexed, and
chunks of deleted documents removed.

Requires the Ollama embedding model to be available:
    ollama pull nomic-embed-text

Usage:
    python scripts/ingest_knowledge_base.py            # add/update documents
    python scripts/ingest_knowledge_base.py --reset    # wipe the collection first (required after
                                                       # changing the embedding model/prefixes)
    python scripts/ingest_knowledge_base.py --force    # re-index every document even if unchanged
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.ingest import ingest_knowledge_base  # noqa: E402
from app.services.rag.store import collection_count, reset_collection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Index the security knowledge base into ChromaDB.")
    parser.add_argument("--reset", action="store_true", help="Delete all existing chunks before ingesting.")
    parser.add_argument("--force", action="store_true", help="Re-index every document even if unchanged.")
    parser.add_argument("--dir", default=None, help="Knowledge base directory (default: data/knowledge_base).")
    args = parser.parse_args()

    if args.reset:
        reset_collection()
        print("Collection reset.")

    summary = ingest_knowledge_base(kb_dir=args.dir, force=args.force)
    print(f"Documents indexed: {summary.documents_processed}")
    print(f"Documents unchanged (skipped): {summary.documents_unchanged}")
    print(f"Chunks indexed: {summary.chunks_indexed}")
    print(f"Stale chunks removed: {summary.chunks_removed}")
    print(f"Total chunks in collection: {collection_count()}")
    if summary.errors:
        print("Errors:")
        for err in summary.errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
