"""The interface languages: every sentence of the app must have an Italian translation."""

import ast
import string
from pathlib import Path

import pytest

from skill_gap import i18n
from skill_gap.translations import ITALIAN

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["app.py", "skill_gap/charts.py", "skill_gap/report.py"]


def _sentences() -> set[str]:
    """Every literal passed to t() or plural() in the code that draws the interface."""
    found = set()
    for source in SOURCES:
        for node in ast.walk(ast.parse((ROOT / source).read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            args = {"t": node.args[:1], "plural": node.args[1:3]}.get(node.func.id, [])
            for arg in args:
                assert isinstance(arg, ast.Constant), f"{source}:{arg.lineno}: t() needs a literal sentence"
                found.add(arg.value)
    return found


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.fixture(autouse=True)
def english_afterwards():
    yield
    i18n.set_language("en")


def test_every_sentence_has_an_italian_translation():
    missing = _sentences() - set(ITALIAN)
    assert not missing, f"Add these to skill_gap/translations.py: {sorted(missing)}"


def test_translations_are_used_and_keep_their_placeholders():
    assert not set(ITALIAN) - _sentences(), "Translations of sentences that are no longer in the app"
    for english, italian in ITALIAN.items():
        assert _placeholders(english) == _placeholders(italian), english


def test_language_switch_and_fallback():
    assert i18n.t("Your results") == "Your results"
    assert i18n.set_language("it") == "it"
    assert i18n.t("Your results") == "I tuoi risultati"
    assert i18n.plural(1, "{n} job post", "{n} job posts") == "1 annuncio"
    assert i18n.plural(3, "{n} job post", "{n} job posts") == "3 annunci"
    assert i18n.t("A sentence without a translation") == "A sentence without a translation"
    assert i18n.set_language("xx") == "en"  # unknown language: English


def test_language_from_browser_locale():
    assert i18n.language_from_locale("it-IT") == "it"
    assert i18n.language_from_locale("en_GB") == "en"
    assert i18n.language_from_locale("de-DE") == "en"
    assert i18n.language_from_locale(None) == "en"


def test_report_is_written_in_the_selected_language(dictionary):
    from skill_gap.analysis import build_skill_table, category_breakdown, split_soft_skills, study_priorities
    from skill_gap.report import build_pdf_report

    table = build_skill_table([{"SQL", "Tableau"}, {"SQL"}], {"SQL"}, dictionary)
    technical, soft = split_soft_skills(table)
    i18n.set_language("it")
    report = build_pdf_report(
        technical, soft, category_breakdown(technical, dictionary), study_priorities(technical), [],
        role=dictionary.domain, n_posts=2, coverage=66.7, nice_weight=0.5, version="test",
        post_matches=[("Post #1 · Data Analyst", 50.0, ["Tableau"]), ("Post #2", None, [])],
    )
    assert report.startswith(b"%PDF")
