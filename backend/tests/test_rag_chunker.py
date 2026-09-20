from app.services.rag.chunker import chunk_text, parse_markdown_document


def test_parse_markdown_document_extracts_frontmatter():
    doc = "---\ntitle: Test Doc\ncategory: playbook\n---\n# Heading\n\nBody text here."
    meta, body = parse_markdown_document(doc)
    assert meta["title"] == "Test Doc"
    assert meta["category"] == "playbook"
    assert body.startswith("# Heading")


def test_parse_markdown_document_without_frontmatter():
    doc = "# Just a heading\n\nNo frontmatter."
    meta, body = parse_markdown_document(doc)
    assert meta == {}
    assert body == doc


def test_chunk_text_splits_long_document_into_multiple_chunks():
    paragraphs = [f"Paragraph number {i} with some extra filler text to add length." for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_chars=200, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200 + 50  # allow small overlap slack


def test_chunk_text_short_document_single_chunk():
    text = "Just one short paragraph."
    chunks = chunk_text(text, max_chars=800)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_handles_empty_input():
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []
