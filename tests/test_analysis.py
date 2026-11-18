"""Tests for the skill table, weighted coverage score and study priorities."""

import pytest

from skill_gap.analysis import (
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    post_matches,
    tied_priorities,
    study_priorities,
)
from skill_gap.extractor import NICE_TO_HAVE, REQUIRED, SkillMention, find_skills_in_posts
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
    # Sorted by demand; ties go to the role's core skills (in the dictionary's order), then A-Z.
    assert list(table["skill"]) == [
        "SQL", "Excel", "Power BI", "Python", "Tableau", "Communication",
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
    assert list(top["skill"]) == ["Excel", "Power BI", "Tableau", "Communication"]
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


def test_soft_skills_are_split_out(dictionary):
    from skill_gap.analysis import split_soft_skills

    posts = [{"SQL", "Teamwork"}, {"SQL", "Communication", "Excel"}]
    table = build_skill_table(posts, {"SQL"}, dictionary)
    technical, soft = split_soft_skills(table)
    assert set(technical["skill"]) == {"SQL", "Excel"}
    assert set(soft["skill"]) == {"Teamwork", "Communication"}
    # Soft skills do not lower the score: SQL 2 out of SQL 2 + Excel 1.
    assert coverage_score(technical) == pytest.approx(100 * 2 / 3)
    assert "Teamwork" not in set(study_priorities(technical)["skill"])


def test_post_matches_ranks_posts_by_weighted_coverage(dictionary):
    posts = [
        {"SQL": REQUIRED, "Tableau": REQUIRED, "Python": NICE_TO_HAVE},   # 1 of 2.5
        {"SQL": REQUIRED, "Excel": NICE_TO_HAVE, "Communication": REQUIRED},  # 1 of 1.5
        {"Communication": REQUIRED},  # soft skills only: nothing to score
    ]
    matches = post_matches(posts, {"SQL"}, dictionary)
    assert list(matches["post"]) == [1, 0, 2]
    best, second, unscored = matches.to_dict("records")
    assert best["coverage"] == pytest.approx(100 * 1 / 1.5)
    assert (best["covered"], best["requested"]) == (1, 2)  # the soft skill is not counted
    assert best["missing_required"] == [] and best["missing_nice"] == ["Excel"]
    assert second["coverage"] == pytest.approx(40.0)
    assert second["missing_required"] == ["Tableau"] and second["missing_nice"] == ["Python"]
    assert second["matched"] == ["SQL"]
    assert unscored["coverage"] is None or unscored["coverage"] != unscored["coverage"]
    assert unscored["requested"] == 0


def test_post_matches_weights_levels_and_nice_weight(dictionary):
    post = {
        "SQL": SkillMention("SQL", REQUIRED, "advanced SQL", level=True),  # 1.5
        "Tableau": SkillMention("Tableau", NICE_TO_HAVE, "Tableau is a plus"),
    }
    assert post_matches([post], {"SQL"}, dictionary)["coverage"][0] == pytest.approx(75.0)
    # With a weight of 0 a missing nice-to-have skill no longer lowers the match.
    assert post_matches([post], {"SQL"}, dictionary, nice_weight=0)["coverage"][0] == pytest.approx(100.0)
    assert post_matches([], {"SQL"}, dictionary).empty


def test_tied_priorities_flags_an_arbitrary_cut(dictionary):
    # Seven missing skills asked once each: the top 5 is cut inside a 7-way tie.
    skills = {"Tableau", "Looker", "Qlik", "dbt", "Jira", "Confluence", "Snowflake"}
    table = build_skill_table([{"SQL"} | skills], {"SQL"}, dictionary)
    assert tied_priorities(table, n=5) == 7
    # A clear-cut top 5 (or fewer missing skills than places) is not flagged.
    clear = build_skill_table([{"Tableau", "Looker"}, {"Tableau"}], set(), dictionary)
    assert tied_priorities(clear, n=1) == 0
    assert tied_priorities(clear, n=5) == 0


def test_core_skills_break_ties(dictionary):
    table = build_skill_table([{"Confluence", "A/B Testing", "Tableau", "Python"}], set(), dictionary)
    # Python and Tableau are core skills of the role; the others follow A-Z.
    assert list(table["skill"]) == ["Python", "Tableau", "A/B Testing", "Confluence"]
