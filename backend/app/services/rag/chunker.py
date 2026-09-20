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


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """Chunk on paragraph/heading boundaries, packing paragraphs up to
    max_chars per chunk with a small overlap for context continuity.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
            continue

        if current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            # single paragraph longer than max_chars: hard-split it
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            current = ""

    if current:
        chunks.append(current)

    return chunks
