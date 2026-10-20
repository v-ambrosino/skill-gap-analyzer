"""Tests for the downloadable HTML report."""

from datetime import date

from skill_gap.analysis import (
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    split_soft_skills,
    study_priorities,
)
from skill_gap.extractor import NICE_TO_HAVE, REQUIRED


def make_report(dictionary, cv_skills):
    from skill_gap.report import build_html_report

    posts = [
        {"SQL": REQUIRED, "Excel": REQUIRED, "Tableau": NICE_TO_HAVE, "Teamwork": REQUIRED},
        {"SQL": REQUIRED, "Power BI": REQUIRED, "Communication": REQUIRED},
    ]
    table = build_skill_table(posts, cv_skills, dictionary)
    technical, soft = split_soft_skills(table)
    return build_html_report(
        technical,
        soft,
        category_breakdown(technical, dictionary),
        study_priorities(technical),
        extra_cv_skills(table, cv_skills),
        role="Data <Analyst>",
        n_posts=len(posts),
        coverage=coverage_score(technical),
        nice_weight=0.5,
        version="1.0.0",
        generated_on=date(2026, 10, 15),
    )


def test_report_content(dictionary):
    html = make_report(dictionary, {"SQL", "Git"})
    assert html.startswith("<!doctype html>")
    # Covered: SQL 2 out of SQL 2 + Excel 1 + Power BI 1 + Tableau 0.5 = 4.5.
    assert "44%" in html
    assert "2026-10-15" in html
    for skill in ["SQL", "Excel", "Power BI", "Tableau"]:
        assert skill in html
    # Skills in the CV that no post asked for.
    assert "not requested by these posts: Git" in html
    # Soft skills have their own section and are not in the score.
    assert "Soft skills to make visible in your CV" in html
    assert "Teamwork" in html and "Communication" in html


def test_report_lists_visible_soft_skills(dictionary):
    html = make_report(dictionary, {"SQL", "Teamwork"})
    assert "Already visible in your CV: Teamwork." in html


def test_report_escapes_text(dictionary):
    html = make_report(dictionary, {"SQL"})
    assert "Data &lt;Analyst&gt;" in html
    assert "Data <Analyst>" not in html


def test_report_full_coverage(dictionary):
    html = make_report(dictionary, {"SQL", "Excel", "Power BI", "Tableau"})
    assert "100%" in html
    assert "Your CV covers every requested skill." in html
