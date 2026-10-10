"""Tests for skill extraction: whole words, synonyms, languages, short names."""

import pytest

from skill_gap.extractor import find_skills, find_skills_in_posts, split_job_posts
from tests.sample_job_posts import (
    CV_EN,
    POST_EN_DATA_ANALYST,
    POST_EN_WITH_R,
    POST_IT_BI_ANALYST,
)


def test_english_post(dictionary):
    found = find_skills(POST_EN_DATA_ANALYST, dictionary)
    expected = {
        "SQL", "Python", "pandas", "NumPy", "Power BI",
        "Dashboarding", "A/B Testing", "Stakeholder Management",
    }
    assert expected <= found
    # "report directly to the Head of Data" is a reporting line, not a skill.
    assert "Reporting" not in found


def test_italian_post_with_accents_and_synonyms(dictionary):
    found = find_skills(POST_IT_BI_ANALYST, dictionary)
    expected = {
        "Excel", "Power BI", "Analytical Thinking", "Teamwork",
        "Tableau", "Data Visualization",
    }
    assert expected <= found
    # In Italian "agile" is also a plain adjective ("ambiente dinamico e agile").
    assert "Agile" not in found


def test_single_letter_r(dictionary):
    found = find_skills(POST_EN_WITH_R, dictionary)
    assert {"R", "SQL", "Python", "Statistics", "Regression Analysis",
            "Time Series Analysis", "SAP"} <= found


@pytest.mark.parametrize(
    "text",
    [
        "Our R&D team is based in Rome.",   # R&D and a word starting with R
        "Contact: Mario R. Rossi",           # middle initial
        "We use SAP R/3 for accounting.",    # product version
        "Strong reporting skills",           # R inside a word
        "r is not a skill in lowercase",     # lowercase r
    ],
)
def test_r_false_positives(dictionary, text):
    assert "R" not in find_skills(text, dictionary)


@pytest.mark.parametrize(
    "text",
    ["Python, R, SQL", "Knowledge of R", "Python or R. We offer", "R programming", "RStudio"],
)
def test_r_true_positives(dictionary, text):
    assert "R" in find_skills(text, dictionary)


def test_case_insensitive(dictionary):
    assert "Tableau" in find_skills("TABLEAU and tableau", dictionary)
    assert "Python" in find_skills("pYtHoN", dictionary)


def test_whole_words_only(dictionary):
    # "sql" must not be found inside NoSQL or MySQL.
    found = find_skills("Experience with NoSQL and MySQL", dictionary)
    assert "SQL" not in found
    assert {"NoSQL", "MySQL"} <= found
    # "excel at" is a verb, not the spreadsheet.
    assert "Excel" not in find_skills("You excel at communication", dictionary)


def test_spelling_variants(dictionary):
    for variant in ["Power BI", "PowerBI", "power-bi", "PBI"]:
        assert "Power BI" in find_skills(variant, dictionary), variant
    assert "Dashboarding" in find_skills("several dashboards", dictionary)  # plural


def test_case_sensitive_short_names(dictionary):
    assert "SAS" in find_skills("Statistical software: SAS", dictionary)
    # "Sas" is an Italian company type, not the SAS software.
    assert "SAS" not in find_skills("Rossi & Bianchi Sas", dictionary)


def test_similar_products_are_separate(dictionary):
    found = find_skills("Reports in Looker Studio", dictionary)
    assert "Looker Studio" in found
    assert "Looker" not in found


def test_cv_extraction(dictionary):
    found = find_skills(CV_EN, dictionary)
    assert {"SQL", "Python", "pandas", "Excel", "Data Visualization",
            "Teamwork", "Reporting", "Dashboarding"} <= found
    # "Jane Q. Example": a middle initial must not become a skill.
    assert "R" not in found


def test_empty_text(dictionary):
    assert find_skills("", dictionary) == set()
    assert find_skills("   \n ", dictionary) == set()


def test_skill_counted_once_per_post(dictionary):
    [skills] = find_skills_in_posts(["SQL SQL SQL and more SQL"], dictionary)
    assert skills == {"SQL"}


def test_split_job_posts():
    text = "---\nFirst post\n---\n\n  ---  \nSecond post\n--\nstill second\n----\n"
    assert split_job_posts(text) == ["First post", "Second post\n--\nstill second"]
    assert split_job_posts("") == []
    # Dashes inside a line are not separators.
    assert split_job_posts("Analyst --- Milan") == ["Analyst --- Milan"]
