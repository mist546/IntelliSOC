"""Knowledge base document management.

The bundled and downloaded documents are indexed by scripts/ingest_knowledge_base.py;
this route lets an analyst see what is indexed and add (or remove) their own
.md/.txt/.pdf documents, kept under data/knowledge_base/custom/, without
leaving the UI.
"""
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_current_user
from app.config import get_settings
from app.schemas.knowledge import KnowledgeDocumentOut, KnowledgeUploadResult
from app.services.rag.chunker import parse_markdown_document
from app.services.rag.embeddings import EmbeddingUnavailableError
from app.services.rag.ingest import category_for, ingest_document, list_knowledge_documents, remove_document_chunks
from app.services.rag.loaders import folder_metadata, humanize_filename, load_document
from app.services.rag.store import IndexMismatchError, get_collection
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
logger = get_logger(__name__)
settings = get_settings()

CUSTOM_SUBDIR = "custom"
UPLOAD_EXTENSIONS = {".md", ".txt", ".pdf"}
MAX_TEXT_DOC_MB = 5
MAX_PDF_DOC_MB = 20
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _kb_root() -> Path:
    return Path(settings.KNOWLEDGE_BASE_DIR)


def _indexed_chunk_counts() -> dict[str, dict]:
    """Group the vector store's chunk metadata by source document."""
    grouped: dict[str, dict] = defaultdict(lambda: {"chunk_count": 0})
    try:
        stored = get_collection().get(include=["metadatas"])
    except Exception as exc:  # noqa: BLE001 - an unreachable store must not break the page
        logger.warning("Could not read knowledge base collection: %s", exc)
        return {}
    for meta in stored.get("metadatas") or []:
        entry = grouped[meta.get("source", "unknown")]
        entry["chunk_count"] += 1
        entry.setdefault("title", meta.get("title", ""))
        entry.setdefault("origin", meta.get("origin", "unknown"))
    return grouped


def _describe_file(path: Path) -> tuple[str | None, str | None]:
    """(title, origin) without loading big files: frontmatter for text,
    _metadata.json for PDFs/JSON."""
    if path.suffix.lower() in (".md", ".txt"):
        meta, _ = parse_markdown_document(path.read_text(encoding="utf-8", errors="replace"))
        return meta.get("title"), meta.get("source")
    extra = folder_metadata(path)
    return extra.get("title"), extra.get("source")


def _is_custom(rel_name: str) -> bool:
    return rel_name.startswith(f"{CUSTOM_SUBDIR}/")


@router.get("", response_model=list[KnowledgeDocumentOut])
def list_documents(_user=Depends(get_current_user)):
    root = _kb_root()
    indexed = _indexed_chunk_counts()
    on_disk = {p.relative_to(root).as_posix(): p for p in list_knowledge_documents(root)} if root.exists() else {}

    docs: list[KnowledgeDocumentOut] = []
    for rel_name in sorted(set(indexed) | set(on_disk)):
        info = indexed.get(rel_name) or {}
        path = on_disk.get(rel_name)
        title, origin = _describe_file(path) if path is not None else (None, None)
        docs.append(
            KnowledgeDocumentOut(
                id=rel_name,
                title=title or info.get("title") or humanize_filename(Path(rel_name)),
                category=category_for(rel_name),
                source=origin or info.get("origin") or "unknown",
                file_type=Path(rel_name).suffix.lower().lstrip("."),
                chunk_count=info.get("chunk_count", 0),
                uploaded_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat() if path else None,
                indexed=bool(info),
                deletable=_is_custom(rel_name),
            )
        )
    return docs


@router.post("", response_model=KnowledgeUploadResult, status_code=201)
async def upload_document(file: UploadFile = File(...), _user=Depends(get_current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {sorted(UPLOAD_EXTENSIONS)}")

    raw_bytes = await file.read()
    limit_mb = MAX_PDF_DOC_MB if suffix == ".pdf" else MAX_TEXT_DOC_MB
    if len(raw_bytes) > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {limit_mb}MB limit")
    if suffix == ".pdf":
        if not raw_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Not a valid PDF file")
    elif not raw_bytes.decode("utf-8", errors="replace").strip():
        raise HTTPException(status_code=400, detail="Document is empty")

    # Sanitise the name: strip any path component and unsafe characters so the
    # file can only ever land inside data/knowledge_base/custom/.
    safe_name = SAFE_NAME_RE.sub("_", Path(file.filename).name).strip("._") or f"document{suffix}"
    target_dir = _kb_root() / CUSTOM_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    target.write_bytes(raw_bytes)
    rel_name = target.relative_to(_kb_root()).as_posix()

    try:
        doc = load_document(target)
    except Exception as exc:  # noqa: BLE001 - corrupt/encrypted PDFs raise various errors
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read the document: {exc}")
    if not doc.sections:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted (is it a scanned PDF? Run OCR on it first, then upload again).",
        )

    base = dict(
        id=rel_name,
        title=doc.title,
        category=category_for(rel_name),
        source=doc.origin if doc.origin not in ("local file", "local PDF") else "analyst upload",
        file_type=suffix.lstrip("."),
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        deletable=True,
    )

    try:
        chunk_count = ingest_document(target, _kb_root(), force=True)
    except (EmbeddingUnavailableError, IndexMismatchError) as exc:
        logger.warning("Knowledge document saved but not indexed: %s", exc)
        return KnowledgeUploadResult(
            **base,
            chunk_count=0,
            indexed=False,
            message=f"Saved to {rel_name} but not indexed ({exc}). Run scripts/ingest_knowledge_base.ps1 once this is resolved.",
        )

    logger.info("Knowledge document %s uploaded and indexed (%d chunks)", rel_name, chunk_count)
    return KnowledgeUploadResult(**base, chunk_count=chunk_count, indexed=True, message=f"Indexed {chunk_count} chunk(s).")


@router.delete("/{doc_id:path}")
def delete_document(doc_id: str, _user=Depends(get_current_user)):
    """Remove an analyst-uploaded document and all of its indexed chunks.
    Bundled/downloaded documents cannot be deleted from the UI."""
    custom_dir = (_kb_root() / CUSTOM_SUBDIR).resolve()
    target = (_kb_root() / doc_id).resolve()
    if not _is_custom(doc_id) or custom_dir not in target.parents:
        raise HTTPException(status_code=403, detail="Only documents in custom/ (analyst uploads) can be deleted")
    removed_chunks = remove_document_chunks(doc_id)
    existed = target.exists()
    target.unlink(missing_ok=True)
    if not existed and not removed_chunks:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": doc_id, "deleted": True, "chunks_removed": removed_chunks}
