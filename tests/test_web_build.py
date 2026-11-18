"""Smoke test of the browser-only build (web/build.py)."""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _build_module():
    spec = importlib.util.spec_from_file_location("web_build", ROOT / "web" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_writes_a_complete_static_site(tmp_path):
    build = _build_module()
    site = tmp_path / "site"
    build.build(site)

    page = (site / "index.html").read_text(encoding="utf-8")
    assert "{{" not in page, "A template placeholder was not filled in"
    assert (site / ".nojekyll").exists()

    # Every file the page tells stlite to load is really in the folder.
    files = json.loads(re.search(r"files: (\{.*?\n\}),", page, re.S).group(1))
    assert "app.py" in files and "skill_gap/i18n.py" in files and ".streamlit/config.toml" in files
    assert any(name.startswith("data/dictionaries/") for name in files)
    assert any(name.startswith("data/samples/") for name in files)
    for name, entry in files.items():
        assert (site / entry["url"]).is_file(), name
    # The demo GIF is heavy and never shown by the app.
    assert not any(name.endswith(".gif") for name in files)


def test_browser_requirements_are_pure_python():
    build = _build_module()
    # pdfplumber needs a compiled library that Pyodide lacks: the app falls back to pypdf.
    assert "pdfplumber" not in build.REQUIREMENTS and "pypdf" in build.REQUIREMENTS


def test_browser_config_has_no_remote_theme_font(tmp_path):
    """A theme font loaded from a URL makes stlite crash at start-up (blank page)."""
    build = _build_module()
    assert build.browser_config('font = "Inter:https://fonts.example/css2?family=Inter"\nbase = "light"\n') == (
        'font = "Inter"\nbase = "light"\n')
    site = tmp_path / "site"
    build.build(site)
    config = (site / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "http" not in config and 'font = "Inter"' in config
    assert "fonts.googleapis.com" in (site / "index.html").read_text(encoding="utf-8")
