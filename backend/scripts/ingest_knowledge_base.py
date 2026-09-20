"""Ingest data/knowledge_base/*.md into the ChromaDB vector store.

Requires the Ollama embedding model to be available:
    ollama pull nomic-embed-text

Usage:
    python scripts/ingest_knowledge_base.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.ingest import ingest_knowledge_base  # noqa: E402


def main() -> None:
    summary = ingest_knowledge_base()
    print(f"Documents processed: {summary.documents_processed}")
    print(f"Chunks indexed: {summary.chunks_indexed}")
    if summary.errors:
        print("Errors:")
        for err in summary.errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
