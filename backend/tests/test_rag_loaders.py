"""Document loaders and chunking: markdown sections, PDF pages (with
page numbers and header/footer removal) and MITRE ATT&CK STIX bundles."""
import json

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.rag.chunker import chunk_text, context_header
from app.services.rag.loaders import clean_pdf_pages, load_document, split_markdown_sections, stix_technique_sections


def test_markdown_sections_keep_heading_path_and_ignore_code_blocks():
    body = "Intro text.\n\n# Brute Force Response\n\n## Containment\n\nBlock the source.\n\n```\n# not a heading\n```\n\n## Recovery\n\nReset passwords."
    sections = split_markdown_sections(body)
    assert [s.heading for s in sections] == [None, "Brute Force Response > Containment", "Brute Force Response > Recovery"]
    assert "# not a heading" in sections[1].text


def _make_pdf(path, pages: list[str]):
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle("Test Incident Guide")
    for number, body in enumerate(pages, start=1):
        pdf.drawString(72, 800, "ACME Security Guide - Confidential")  # running header
        y = 760
        for line in body.split("\n"):
            pdf.drawString(72, y, line)
            y -= 16
        pdf.drawString(300, 40, str(number))  # page number footer
        pdf.showPage()
    pdf.save()


def test_pdf_pages_keep_page_numbers_and_drop_running_headers(tmp_path):
    pages = [
        "Chapter one explains how security incidents are detected and then reported by staff members.",
        "Chapter two covers containment: isolate affected hosts and preserve evidence first.",
        "Chapter three covers eradication and recovery after an incident has been contained.",
        "Chapter four covers lessons learned and improving detection after every incident.",
    ]
    path = tmp_path / "guide.pdf"
    _make_pdf(path, pages)

    doc = load_document(path)
    assert doc.title == "Test Incident Guide"  # from the PDF metadata
    assert [s.page for s in doc.sections] == [1, 2, 3, 4]
    assert "containment" in doc.sections[1].text
    assert all("ACME Security Guide" not in s.text for s in doc.sections)


def test_pdf_title_from_folder_metadata(tmp_path):
    path = tmp_path / "sp_800_x.pdf"
    _make_pdf(path, ["Some guidance text that is long enough to be kept as a page section."])
    (tmp_path / "_metadata.json").write_text(json.dumps({"sp_800_x.pdf": {"title": "NIST SP 800-X", "source": "https://nist"}}))
    doc = load_document(path)
    assert doc.title == "NIST SP 800-X" and doc.origin == "https://nist"


def test_clean_pdf_pages_rejoins_hyphenation_and_wrapped_lines():
    cleaned = clean_pdf_pages(["The attacker used creden-\ntial stuffing against\nthe login page."])
    assert cleaned == ["The attacker used credential stuffing against the login page."]


STIX = {
    "type": "bundle",
    "objects": [
        {"id": "attack-pattern--1", "type": "attack-pattern", "name": "Brute Force",
         "description": "Adversaries may use brute force techniques (Citation: X).",
         "kill_chain_phases": [{"phase_name": "credential-access"}], "x_mitre_platforms": ["Linux", "Windows"],
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1110"}]},
        {"id": "attack-pattern--2", "type": "attack-pattern", "name": "Old", "revoked": True,
         "external_references": [{"source_name": "mitre-attack", "external_id": "T9999"}]},
        {"id": "course-of-action--mfa", "type": "course-of-action", "name": "Multi-factor Authentication",
         "external_references": [{"source_name": "mitre-attack", "external_id": "M1032"}]},
        {"id": "course-of-action--dep", "type": "course-of-action", "name": "Deprecated", "x_mitre_deprecated": True,
         "external_references": [{"source_name": "mitre-attack", "external_id": "M0000"}]},
        {"id": "relationship--a", "type": "relationship", "relationship_type": "mitigates",
         "source_ref": "course-of-action--mfa", "target_ref": "attack-pattern--1", "description": "Require MFA."},
        {"id": "relationship--b", "type": "relationship", "relationship_type": "mitigates",
         "source_ref": "course-of-action--dep", "target_ref": "attack-pattern--1"},
    ],
}


def test_stix_bundle_becomes_one_section_per_live_technique_with_mitigations(tmp_path):
    sections = stix_technique_sections(STIX)
    assert [s.extra["technique_id"] for s in sections] == ["T1110"]  # revoked T9999 skipped
    text = sections[0].text
    assert text.startswith("T1110 Brute Force")
    assert "credential access" in text and "Linux, Windows" in text
    assert "Mitigations: M1032 Multi-factor Authentication: Require MFA." in text
    assert "M0000" not in text and "(Citation" not in text

    path = tmp_path / "enterprise_attack.json"
    path.write_text(json.dumps(STIX))
    assert load_document(path).title == "MITRE ATT&CK Enterprise"


def test_chunk_overlap_starts_on_a_word_and_long_paragraphs_split_on_sentences():
    para = " ".join(f"Sentence number {i} explains one detail." for i in range(60))
    chunks = chunk_text(para, max_chars=300, overlap=60)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    assert all(c.split()[0][0].isalnum() for c in chunks)  # never starts mid-word


def test_context_header():
    assert context_header("NIST SP 800-61", page=14) == "[NIST SP 800-61 | p. 14]"
    assert context_header("Brute Force Response", "Brute Force Response > Containment") == "[Brute Force Response > Containment]"
    assert context_header("Guide", "Containment") == "[Guide > Containment]"


def test_headings_are_cleaned_of_images_links_and_attributes():
    body = "# A03:2021 – Injection    ![icon](assets/icon.png){: style=\"height:80px\"}\n\nText.\n\n## See [OWASP](https://owasp.org)\n\nMore."
    sections = split_markdown_sections(body)
    assert [s.heading for s in sections] == ["A03:2021 – Injection", "A03:2021 – Injection > See OWASP"]
