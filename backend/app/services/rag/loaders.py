"""Turn knowledge base files into titled, sectioned text ready for chunking.

Supported formats:
  .md / .txt   split on markdown headings, keeping the heading path so
               every chunk knows which part of which document it came from
  .pdf         one section per page (page numbers are kept for citations);
               repeated page headers/footers are stripped
  .json        a MITRE ATT&CK STIX bundle (enterprise-attack.json): one
               section per live technique with its tactics, platforms,
               detection notes and mitigations

A folder may contain an optional `_metadata.json` mapping file names to a
display title and source URL - used for PDFs, which have no frontmatter:
    {"sp_800_61_rev3.pdf": {"title": "NIST SP 800-61 Rev. 3", "source": "https://..."}}
"""
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.services.rag.chunker import parse_markdown_document

METADATA_FILE = "_metadata.json"

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$")
CITATION_RE = re.compile(r"\(Citation:[^)]*\)")
MIN_PDF_PAGE_CHARS = 80


class UnsupportedDocumentError(ValueError):
    pass


@dataclass
class Section:
    text: str
    heading: str | None = None
    page: int | None = None
    extra: dict = field(default_factory=dict)  # e.g. {"technique_id": "T1110"}


@dataclass
class LoadedDocument:
    title: str
    origin: str
    sections: list[Section]


def humanize_filename(path: Path) -> str:
    return re.sub(r"[_\-]+", " ", path.stem).strip().title()


def folder_metadata(path: Path) -> dict:
    meta_file = path.parent / METADATA_FILE
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get(path.name, {})
    except (OSError, json.JSONDecodeError):
        return {}


def load_document(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return _load_markdown(path)
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".json":
        return _load_stix(path)
    raise UnsupportedDocumentError(f"Unsupported document type: {path.name}")


# ---- markdown / text ---------------------------------------------------------


def _clean_heading(heading: str) -> str:
    """Drop images, link targets and {: attribute} blocks that some sources
    (e.g. the OWASP Top 10 site) put inside headings."""
    heading = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", heading)
    heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
    heading = re.sub(r"\{:[^}]*\}", "", heading)
    return re.sub(r"\s+", " ", heading).strip()


def split_markdown_sections(body: str) -> list[Section]:
    """Split on #..#### headings. Each section's heading is the path of
    enclosing headings, e.g. "Brute Force Response > Containment"."""
    sections: list[Section] = []
    path: list[tuple[int, str]] = []
    lines: list[str] = []

    def flush():
        text = "\n".join(lines).strip()
        if text:
            sections.append(Section(text=text, heading=" > ".join(h for _, h in path) or None))
        lines.clear()

    in_code_block = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        match = None if in_code_block else HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            path = [(lvl, h) for lvl, h in path if lvl < level] + [(level, _clean_heading(match.group(2)))]
        else:
            lines.append(line)
    flush()
    return sections


def _load_markdown(path: Path) -> LoadedDocument:
    meta, body = parse_markdown_document(path.read_text(encoding="utf-8", errors="replace"))
    extra = folder_metadata(path)
    return LoadedDocument(
        title=meta.get("title") or extra.get("title") or humanize_filename(path),
        origin=meta.get("source") or extra.get("source") or "local file",
        sections=split_markdown_sections(body),
    )


# ---- PDF -------------------------------------------------------------------------


def _normalise_line(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def clean_pdf_pages(pages: list[str]) -> list[str]:
    """Strip running headers/footers and page-number lines, then undo PDF
    line wrapping so each page becomes readable paragraphs."""
    page_lines = [[ln.strip() for ln in page.splitlines()] for page in pages]

    # A line (ignoring digits) that appears on more than half of the pages is
    # a running header or footer, e.g. "NIST SP 800-61r3  April 2025  12".
    repeated: set[str] = set()
    if len(pages) >= 4:
        counts: Counter = Counter()
        for lines in page_lines:
            counts.update({_normalise_line(ln) for ln in lines if ln})
        repeated = {ln for ln, n in counts.items() if n > len(pages) / 2 and len(ln) < 120}

    cleaned: list[str] = []
    for lines in page_lines:
        kept = [
            ln for ln in lines
            if ln and _normalise_line(ln) not in repeated and not re.fullmatch(r"(page\s*)?(#+|[ivx]{1,6})", _normalise_line(ln))
        ]
        text = "\n".join(kept)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join hyphenated words
        text = re.sub(r"[ \t]+", " ", text)
        # Join wrapped lines; keep breaks after sentence ends and before bullets/numbers.
        text = re.sub(r"(?<![.:;!?])\n(?![•\-•\d])", " ", text)
        cleaned.append(text.strip())
    return cleaned


def _load_pdf(path: Path) -> LoadedDocument:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    raw_pages = [(page.extract_text() or "") for page in reader.pages]
    pages = clean_pdf_pages(raw_pages)
    sections = [
        Section(text=text, page=number)
        for number, text in enumerate(pages, start=1)
        if len(text) >= MIN_PDF_PAGE_CHARS
    ]

    extra = folder_metadata(path)
    pdf_title = (reader.metadata.title if reader.metadata and reader.metadata.title else "") or ""
    title = extra.get("title") or (pdf_title.strip() if len(pdf_title.strip()) > 5 else "") or humanize_filename(path)
    return LoadedDocument(title=title, origin=extra.get("source") or "local PDF", sections=sections)


# ---- MITRE ATT&CK STIX ------------------------------------------------------------


def attack_id(obj: dict) -> str | None:
    return next(
        (r["external_id"] for r in obj.get("external_references", []) if r.get("source_name") == "mitre-attack"),
        None,
    )


def is_live(obj: dict) -> bool:
    return not obj.get("revoked") and not obj.get("x_mitre_deprecated")


def _clean_stix_text(text: str) -> str:
    text = CITATION_RE.sub("", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # markdown links -> their text
    return re.sub(r"[ \t]+", " ", text).strip()


def stix_technique_sections(bundle: dict) -> list[Section]:
    """One section per live ATT&CK technique/sub-technique, including the
    names of the mitigations linked to it by `mitigates` relationships."""
    objects = bundle.get("objects", [])
    by_stix_id = {o["id"]: o for o in objects if "id" in o}

    mitigations: dict[str, list[str]] = defaultdict(list)
    for rel in objects:
        if rel.get("type") != "relationship" or rel.get("relationship_type") != "mitigates" or not is_live(rel):
            continue
        source = by_stix_id.get(rel.get("source_ref"), {})
        if source.get("type") != "course-of-action" or not is_live(source) or not attack_id(source):
            continue
        how = _clean_stix_text(rel.get("description", ""))[:300]
        mitigations[rel["target_ref"]].append(f"{attack_id(source)} {source.get('name', '')}" + (f": {how}" if how else ""))

    sections: list[Section] = []
    for obj in objects:
        if obj.get("type") != "attack-pattern" or not is_live(obj):
            continue
        tid = attack_id(obj)
        if not tid:
            continue
        tactics = ", ".join(p["phase_name"].replace("-", " ") for p in obj.get("kill_chain_phases") or [])
        parts = [
            f"{tid} {obj.get('name', '')}",
            f"Tactics: {tactics or 'n/a'}. Platforms: {', '.join(obj.get('x_mitre_platforms', [])) or 'n/a'}.",
            _clean_stix_text(obj.get("description", "")),
        ]
        detection = _clean_stix_text(obj.get("x_mitre_detection", ""))
        if detection:
            parts.append(f"Detection: {detection}")
        if mitigations.get(obj["id"]):
            parts.append("Mitigations: " + "; ".join(sorted(mitigations[obj["id"]])))
        sections.append(Section(text="\n\n".join(parts), heading=f"{tid} {obj.get('name', '')}", extra={"technique_id": tid}))
    sections.sort(key=lambda s: s.extra["technique_id"])
    return sections


def _load_stix(path: Path) -> LoadedDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("type") != "bundle":
        raise UnsupportedDocumentError(f"{path.name} is not a STIX bundle (only MITRE ATT&CK STIX JSON is supported)")
    extra = folder_metadata(path)
    return LoadedDocument(
        title=extra.get("title") or "MITRE ATT&CK Enterprise",
        origin=extra.get("source") or "MITRE ATT&CK STIX",
        sections=stix_technique_sections(data),
    )
