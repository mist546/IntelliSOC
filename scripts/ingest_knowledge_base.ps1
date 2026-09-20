# Ingests data/knowledge_base/*.md into the local ChromaDB vector store.
# Requires Ollama running with the embedding model pulled:
#   ollama pull nomic-embed-text
# Run from the project root: .\scripts\ingest_knowledge_base.ps1

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
& ".\.venv\Scripts\python.exe" scripts\ingest_knowledge_base.py
