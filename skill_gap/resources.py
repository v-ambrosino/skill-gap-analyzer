"""Free learning resources for each skill (data/learning_resources.yaml).

Skills without a curated entry get a web search link, so every study
priority comes with somewhere to start.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus

import yaml

RESOURCES_PATH = Path(__file__).resolve().parent.parent / "data" / "learning_resources.yaml"


def load_resources(path: str | Path = RESOURCES_PATH) -> dict[str, list[tuple[str, str]]]:
    """Skill name -> list of (title, url)."""
    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return {skill: [(str(t), str(u)) for t, u in items] for skill, items in data.items()}


def resources_for(skill: str, resources: dict[str, list[tuple[str, str]]]) -> list[tuple[str, str]]:
    """Curated resources for `skill`, or a search link when there are none."""
    if skill in resources:
        return resources[skill]
    return [(f"Search free courses for {skill}",
             "https://www.google.com/search?q=" + quote_plus(f"learn {skill} free course"))]
