# Indexes data/knowledge_base/ (.md, .txt, .pdf, MITRE STIX .json) into the local ChromaDB vector store.
# Requires Ollama running with the embedding model pulled:
#   ollama pull nomic-embed-text
# Run from the project root: .\scripts\ingest_knowledge_base.ps1
# Incremental by default (unchanged documents are skipped, deleted ones removed).
#   -Reset  wipe the collection first (required after changing the embedding model)
#   -Force  re-index every document even if unchanged
param([switch]$Reset, [switch]$Force)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
$extra = @()
if ($Reset) { $extra += "--reset" }
if ($Force) { $extra += "--force" }
& ".\.venv\Scripts\python.exe" scripts\ingest_knowledge_base.py @extra
