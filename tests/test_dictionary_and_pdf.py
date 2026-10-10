"""Tests for the dictionary loader/validator and the PDF reader."""

import pytest

from skill_gap.pdf_reader import PdfReadError, extract_text_from_pdf
from skill_gap.skills_dictionary import DictionaryError, parse_dictionary


def test_shipped_dictionary_is_valid(dictionary):
    assert 80 <= len(dictionary.skills) <= 120
    names = [skill.name for skill in dictionary.skills]
    assert len(names) == len(set(names))
    assert {skill.category for skill in dictionary.skills} <= set(dictionary.categories)


def _minimal(skills):
    return {"categories": ["Tools"], "skills": skills}


def test_unknown_category_is_rejected():
    with pytest.raises(DictionaryError, match="unknown category"):
        parse_dictionary(_minimal([{"name": "X", "category": "Nope", "synonyms": ["x"]}]))


def test_skill_without_matchers_is_rejected():
    with pytest.raises(DictionaryError, match="no synonyms"):
        parse_dictionary(_minimal([{"name": "X", "category": "Tools"}]))


def test_shared_synonym_is_rejected():
    skills = [
        {"name": "A", "category": "Tools", "synonyms": ["bi tool"]},
        {"name": "B", "category": "Tools", "synonyms": ["BI Tool"]},
    ]
    with pytest.raises(DictionaryError, match="used by both"):
        parse_dictionary(_minimal(skills))


def test_invalid_regex_is_rejected():
    with pytest.raises(DictionaryError, match="invalid pattern"):
        parse_dictionary(_minimal([{"name": "X", "category": "Tools", "patterns": ["("]}]))


def _make_pdf(text: str) -> bytes:
    """Build a tiny one-page PDF by hand, so the tests need no extra library."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_start = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_start,
    )
    return pdf


def test_extract_text_from_pdf():
    text = extract_text_from_pdf(_make_pdf("Skills: SQL, Python, Power BI"))
    assert "SQL, Python, Power BI" in text


def test_invalid_pdf_raises():
    with pytest.raises(PdfReadError):
        extract_text_from_pdf(b"this is not a pdf")
    with pytest.raises(PdfReadError):
        extract_text_from_pdf(b"")
