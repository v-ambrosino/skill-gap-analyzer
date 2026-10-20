"""Assemble the browser-only version of the app (stlite) into a static folder.

stlite runs Streamlit and Python inside the browser via Pyodide (WebAssembly),
so the CV is never uploaded anywhere: it stays on the visitor's device.

Usage:
    python web/build.py [output_dir]   # default: _site

The output folder can be served by any static host (GitHub Pages is set up in
.github/workflows/pages.yml). To try it locally:
    python web/build.py && python -m http.server -d _site 8000
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STLITE_VERSION = "1.11.0"
# pdfplumber needs a compiled library unavailable in Pyodide: the app falls back to pypdf.
REQUIREMENTS = ["pandas", "plotly", "PyYAML", "fpdf2", "pypdf"]
SOURCES = ["app.py", "skill_gap", "data", "assets", ".streamlit/config.toml"]


def collect_files() -> list[str]:
    """Every file the app needs at runtime, as paths relative to the repo root."""
    files: list[str] = []
    for source in SOURCES:
        path = ROOT / source
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for file in candidates:
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".gif":
                files.append(file.relative_to(ROOT).as_posix())
    return files


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    files = collect_files()
    for name in files:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)

    template = (ROOT / "web" / "index.template.html").read_text(encoding="utf-8")
    html = (
        template.replace("{{STLITE_VERSION}}", STLITE_VERSION)
        .replace("{{REQUIREMENTS}}", json.dumps(REQUIREMENTS))
        .replace("{{FILES}}", json.dumps({name: {"url": name} for name in files}, indent=2))
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / ".nojekyll").touch()  # GitHub Pages must serve the .streamlit folder
    print(f"Built {len(files)} files into {output}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site")
