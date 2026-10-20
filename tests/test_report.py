"""Tests for the downloadable PDF report."""

from datetime import date
from io import BytesIO

import pdfplumber

from skill_gap.analysis import (
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    split_soft_skills,
    study_priorities,
)
from skill_gap.extractor import NICE_TO_HAVE, REQUIRED
from skill_gap.report import build_pdf_report


def make_report(dictionary, cv_skills) -> bytes:
    posts = [
        {"SQL": REQUIRED, "Excel": REQUIRED, "Tableau": NICE_TO_HAVE, "Teamwork": REQUIRED},
        {"SQL": REQUIRED, "Power BI": REQUIRED, "Communication": REQUIRED},
    ]
    table = build_skill_table(posts, cv_skills, dictionary)
    technical, soft = split_soft_skills(table)
    return build_pdf_report(
        technical,
        soft,
        category_breakdown(technical, dictionary),
        study_priorities(technical),
        extra_cv_skills(table, cv_skills),
        role="Data Analyst / BI / Business Analyst",
        n_posts=len(posts),
        coverage=coverage_score(technical),
        nice_weight=0.5,
        version="1.1.0",
        generated_on=date(2026, 10, 20),
        cv_phrases={"Teamwork": ["Worked in a cross-functional team of 5."]},
    )


def pdf_text(pdf: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf)) as doc:
        return "\n".join(page.extract_text() or "" for page in doc.pages)


def test_report_is_a_pdf_with_the_results(dictionary):
    pdf = make_report(dictionary, {"SQL", "Git"})
    assert pdf.startswith(b"%PDF")
    text = pdf_text(pdf)
    # Covered: SQL 2 out of SQL 2 + Excel 1 + Power BI 1 + Tableau 0.5 = 4.5.
    assert "44%" in text
    assert "2026-10-20" in text
    for skill in ["SQL", "Excel", "Power BI", "Tableau"]:
        assert skill in text
    assert "Also in your CV but not requested: Git." in text
    # Soft skills have their own section.
    assert "Soft skills to make visible in your CV" in text
    assert "Teamwork" in text and "Communication" in text


def test_report_full_coverage(dictionary):
    text = pdf_text(make_report(dictionary, {"SQL", "Excel", "Power BI", "Tableau", "Teamwork"}))
    assert "100%" in text
    assert "Your CV covers every requested technical skill." in text
    assert "Already visible in your CV: Teamwork." in text


def test_report_links_learning_resources(dictionary):
    text = pdf_text(make_report(dictionary, {"SQL"}))
    assert "Where to start learning (free):" in text


def test_report_suggests_cv_sentences_for_missing_soft_skills(dictionary):
    text = pdf_text(make_report(dictionary, {"SQL"}))
    assert "Example sentences for your CV:" in text
    assert "Teamwork: Worked in a cross-functional team of 5." in text
