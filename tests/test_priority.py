"""Tests for required vs nice-to-have detection and evidence snippets."""

import pytest

from skill_gap.analysis import build_skill_table, coverage_score, study_priorities
from skill_gap.extractor import NICE_TO_HAVE, REQUIRED, find_skill_mentions

POST_WITH_SECTIONS = """
Data Analyst (fictional)
Requirements:
- Strong SQL and Excel
- Fluent English; German is a plus
Nice to have:
- Tableau
- Experience with dbt
Responsibilities:
- Build dashboards in Power BI
"""


def priorities(text, dictionary):
    return {k: v.priority for k, v in find_skill_mentions(text, dictionary).items()}


def test_section_headers(dictionary):
    found = priorities(POST_WITH_SECTIONS, dictionary)
    for skill in ["SQL", "Excel", "English", "Power BI", "Dashboarding"]:
        assert found[skill] == REQUIRED, skill
    # Under "Nice to have:" until "Responsibilities:" starts a new section.
    assert found["Tableau"] == NICE_TO_HAVE
    assert found["dbt"] == NICE_TO_HAVE


@pytest.mark.parametrize(
    "text, skill",
    [
        ("Python is a plus", "Python"),
        ("Experience with Looker would be a plus.", "Looker"),
        ("Gradita la conoscenza di Tableau", "Tableau"),
        ("Costituisce titolo preferenziale la conoscenza di R.", "R"),
        ("La conoscenza di SAS è un plus", "SAS"),
        ("Bonus: Airflow", "Apache Airflow"),
        ("Preferibilmente esperienza con Qlik", "Qlik"),
    ],
)
def test_inline_markers(dictionary, text, skill):
    assert priorities(text, dictionary)[skill] == NICE_TO_HAVE


def test_markers_only_apply_to_their_clause(dictionary):
    found = priorities("Fluent English; Python is a plus. Strong SQL skills.", dictionary)
    assert found == {"English": REQUIRED, "Python": NICE_TO_HAVE, "SQL": REQUIRED}


def test_markers_in_brackets_only_apply_to_the_brackets(dictionary):
    found = priorities("SQL (BigQuery preferred)", dictionary)
    assert found == {"SQL": REQUIRED, "BigQuery": NICE_TO_HAVE}
    # ...but a marker outside the brackets applies to all of them.
    found = priorities("Basic Python (pandas) is a plus", dictionary)
    assert found == {"Python": NICE_TO_HAVE, "pandas": NICE_TO_HAVE}


def test_required_mention_wins(dictionary):
    text = "Requirements: SQL and Python.\nNice to have: Python libraries like pandas."
    found = priorities(text, dictionary)
    assert found["Python"] == REQUIRED
    assert found["pandas"] == NICE_TO_HAVE


def test_skill_lines_are_not_headers(dictionary):
    # "SQL (BigQuery preferred)" mentions a skill, so it must not start a
    # nice-to-have section for the following lines.
    found = priorities("SQL (BigQuery preferred)\nExcel", dictionary)
    assert found["Excel"] == REQUIRED


def test_snippets(dictionary):
    mentions = find_skill_mentions("Requisiti:\n- Capacità analitiche e lavoro in team", dictionary)
    # The snippet keeps the original text, accents included.
    assert mentions["Analytical Thinking"].snippet == "Capacità analitiche e lavoro in team"


def test_nice_to_have_weight(dictionary):
    posts = [{"SQL": REQUIRED, "Tableau": NICE_TO_HAVE}, {"SQL": REQUIRED}]
    table = build_skill_table(posts, {"Tableau"}, dictionary).set_index("skill")
    assert table.loc["SQL", "demand"] == 2
    assert table.loc["Tableau", "demand"] == 0.5
    assert table.loc["Tableau", "nice_count"] == 1
    # Covered: Tableau 0.5 out of 2.5.
    assert coverage_score(table.reset_index()) == pytest.approx(20.0)

    # Weight 0: nice-to-have skills are ignored by the score and the priorities.
    ignored = build_skill_table(posts, {"SQL"}, dictionary, nice_weight=0)
    assert coverage_score(ignored) == 100.0
    assert study_priorities(ignored).empty
