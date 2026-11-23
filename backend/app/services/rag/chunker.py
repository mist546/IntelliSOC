import re

FRONTMATTER_RE = re.compile(r"^---\n(?P<meta>.*?)\n---\n(?P<body>.*)$", re.DOTALL)


def parse_markdown_document(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group("meta").splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, match.group("body").strip()


def context_header(title: str, heading: str | None = None, page: int | None = None) -> str:
    """Prefix stored with every chunk, e.g. "[NIST SP 800-61 Rev. 3 | p. 14]" or
    "[Brute Force Response > Containment]", so a chunk is understandable - to
    the embedding model, the LLM and the analyst - without its document."""
    label = title
    if heading and heading != title:
        label = heading if heading.startswith(title) else f"{title} > {heading}"
    return f"[{label} | p. {page}]" if page else f"[{label}]"


def _tail(text: str, overlap: int) -> str:
    """The last ~`overlap` characters of text, starting at a word boundary."""
    tail = text[-overlap:]
    space = tail.find(" ")
    return tail[space + 1 :] if 0 <= space < len(tail) - 1 else tail


def _split_long(paragraph: str, max_chars: int) -> list[str]:
    """Split an over-long paragraph at sentence ends (else word boundaries)."""
    pieces: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > max_chars:  # a single enormous "sentence"
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + len(sentence) + 1 > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """Chunk on paragraph boundaries, packing paragraphs up to max_chars per
    chunk, with a small word-aligned overlap for context continuity."""
    paragraphs: list[str] = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if para:
            paragraphs.extend(_split_long(para, max_chars) if len(para) > max_chars else [para])

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
            continue
        if current:
            chunks.append(current)
        tail = _tail(current, overlap) if current and overlap else ""
        current = f"{tail}\n\n{para}" if tail and len(tail) + len(para) + 2 <= max_chars else para

    if current:
        chunks.append(current)
    return chunks
