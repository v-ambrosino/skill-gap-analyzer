"""Tests for the skill table, weighted coverage score and study priorities."""

import pytest

from skill_gap.analysis import (
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    study_priorities,
)
from skill_gap.extractor import find_skills_in_posts
from tests.sample_job_posts import POSTS_FOR_ANALYSIS


@pytest.fixture
def table(dictionary):
    posts_skills = find_skills_in_posts(POSTS_FOR_ANALYSIS, dictionary)
    cv_skills = {"SQL", "Python", "Git"}
    return build_skill_table(posts_skills, cv_skills, dictionary)


def test_skill_table_counts(table):
    counts = dict(zip(table["skill"], table["posts_count"]))
    assert counts == {
        "SQL": 3, "Excel": 2, "Power BI": 1, "Python": 1,
        "Tableau": 1, "Communication": 1,
    }
    # Sorted by demand, ties alphabetically.
    assert list(table["skill"]) == [
        "SQL", "Excel", "Communication", "Power BI", "Python", "Tableau",
    ]
    assert table.loc[table["skill"] == "SQL", "posts_share"].item() == 1.0


def test_coverage_is_weighted(table):
    # Covered: SQL (3) + Python (1) = 4 out of a total weight of 9.
    assert coverage_score(table) == pytest.approx(100 * 4 / 9)


def test_coverage_edge_cases(dictionary):
    empty = build_skill_table([set(), set()], {"SQL"}, dictionary)
    assert coverage_score(empty) is None

    full = build_skill_table([{"SQL"}, {"SQL", "Excel"}], {"SQL", "Excel"}, dictionary)
    assert coverage_score(full) == 100.0


def test_study_priorities(table):
    top = study_priorities(table, n=5)
    assert list(top["skill"]) == ["Excel", "Communication", "Power BI", "Tableau"]
    assert not top["in_cv"].any()
    assert len(study_priorities(table, n=2)) == 2


def test_category_breakdown(table, dictionary):
    breakdown = category_breakdown(table, dictionary).set_index("category")
    # Category order follows the dictionary.
    assert list(breakdown.index) == ["Tools", "Programming & Data", "Soft Skills"]
    assert breakdown.loc["Programming & Data", "coverage_pct"] == 100.0
    assert breakdown.loc["Tools", "coverage_pct"] == 0.0


def test_extra_cv_skills(table):
    assert extra_cv_skills(table, {"SQL", "Python", "Git"}) == ["Git"]
