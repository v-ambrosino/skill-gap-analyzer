"""The Streamlit interface, run headless with Streamlit's own test client.

These tests catch what the unit tests cannot: a page that does not render, a
button that raises, a results tab that disappears.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _app(**query) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=60)
    for key, value in query.items():
        app.query_params[key] = value
    return app.run()


def _button(app: AppTest, key_or_label: str):
    for button in app.button:
        if key_or_label in (button.key, button.label):
            return button
    raise AssertionError(f"No button {key_or_label!r}: {[b.label for b in app.button]}")


def _text(app: AppTest) -> str:
    return "\n".join(str(element.value) for element in app.markdown)


def test_landing_page_renders_with_analyze_disabled():
    app = _app()
    assert not app.exception
    assert "Find your" in _text(app)
    assert _button(app, "analyze").disabled
    assert not app.tabs  # no results before an analysis


def test_sample_data_shows_results_in_every_tab():
    app = _app()
    _button(app, "Try with sample data").click().run()
    assert not app.exception
    assert [tab.label.split(": ")[-1] for tab in app.tabs] == [
        "Overview", "Job posts", "Skills", "Evidence", "Report"]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Job posts"] == "4"
    assert metrics["Weighted coverage"].endswith("%")
    text = _text(app)
    assert "Which job posts fit you best" in text and "sga-match-item" in text
    # Four posts are too few for a reliable ranking: the app says so.
    assert any("Based on only 4 job posts" in str(w.value) for w in app.warning)
    assert not _button(app, "analyze").disabled


@pytest.mark.parametrize("role", [
    "Digital Marketing / Communication", "Finance / Accounting / Controlling",
    "Human Resources / Recruiter", "Project Manager / Operations",
    "Sales / Account Manager / Customer Success", "Software Developer / Web Developer",
])
def test_every_role_has_its_own_sample(role):
    app = _app()
    app.selectbox(key="role").set_value(role).run()
    _button(app, "Try with sample data").click().run()
    assert not app.exception
    assert app.selectbox(key="role").value == role  # no fallback to the default role
    assert app.tabs


def test_italian_interface():
    app = _app(lang="it")
    assert not app.exception
    assert "Scopri il tuo" in _text(app)
    _button(app, "Prova con dati di esempio").click().run()
    assert not app.exception
    assert "I tuoi risultati" in _text(app)
    assert "Copertura pesata" in {metric.label for metric in app.metric}


def test_clear_all_removes_the_results():
    app = _app()
    _button(app, "Try with sample data").click().run()
    assert app.tabs
    _button(app, "Clear all").click().run()
    assert not app.exception
    assert not app.tabs
    assert _button(app, "analyze").disabled
