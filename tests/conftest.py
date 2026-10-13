import sys
from pathlib import Path

import pytest

# Make the project root importable when running `pytest` from any folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skill_gap.skills_dictionary import load_dictionary  # noqa: E402


@pytest.fixture(scope="session")
def dictionary():
    """The real dictionary shipped with the app (data/dictionaries/data_analytics.yaml)."""
    return load_dictionary()
