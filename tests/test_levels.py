"""Skill levels ("advanced Excel", "3+ years of SQL") weigh more."""

from skill_gap.analysis import LEVEL_BONUS, build_skill_table
from skill_gap.extractor import find_skill_mentions


def levels(text, dictionary):
    return {name for name, m in find_skill_mentions(text, dictionary).items() if m.level}


def test_level_words_and_years_in_several_languages(dictionary):
    assert levels("Advanced Excel and Power BI.\nGood knowledge of Tableau.", dictionary) == {"Excel"}
    assert levels("SQL (3+ years) required.", dictionary) == {"SQL"}
    assert levels("At least 5 years of experience with Python.", dictionary) == {"Python"}
    assert levels("Ottima conoscenza di Excel.", dictionary) == {"Excel"}
    assert levels("Excel avancé; connaissance de SQL.", dictionary) == {"Excel"}
    assert levels("Fundierte SQL-Kenntnisse.", dictionary) == {"SQL"}
    assert levels("Experiencia con Tableau.", dictionary) == set()


def test_level_adds_demand(dictionary):
    posts = [
        find_skill_mentions("Advanced SQL. Excel.", dictionary),
        find_skill_mentions("SQL and Excel.", dictionary),
    ]
    table = build_skill_table(posts, set(), dictionary).set_index("skill")
    assert table.loc["SQL", "level_count"] == 1
    assert table.loc["SQL", "demand"] == 2 + LEVEL_BONUS
    assert table.loc["Excel", "demand"] == 2
