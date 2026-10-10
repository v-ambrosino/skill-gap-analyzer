"""Find dictionary skills in free text (a CV or a job post).

The approach is deliberately simple and explainable: no AI, no external API.
A skill is "found" when at least one of its synonyms appears in the text as a
whole word. Each skill counts at most once per document, so the analysis
measures "in how many job posts is this skill requested", which is more
robust than counting raw mentions (a post repeating "Excel" five times is
still one employer asking for Excel).
"""

from __future__ import annotations

import re

from skill_gap.normalization import normalize_text
from skill_gap.skills_dictionary import SkillDictionary

# A separator line made only of three or more dashes, e.g. "---".
_POST_SEPARATOR = re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE)


def find_skills(text: str, dictionary: SkillDictionary) -> set[str]:
    """Return the names of the dictionary skills that appear in `text`."""
    if not text or not text.strip():
        return set()
    normalized = normalize_text(text)
    return {skill.name for skill in dictionary.skills if skill.is_in(normalized)}


def split_job_posts(text: str) -> list[str]:
    """Split a block of pasted text into job posts on lines containing "---".

    Empty chunks (e.g. a separator at the very start) are dropped.
    """
    if not text:
        return []
    return [chunk.strip() for chunk in _POST_SEPARATOR.split(text) if chunk.strip()]


def find_skills_in_posts(posts: list[str], dictionary: SkillDictionary) -> list[set[str]]:
    """Run `find_skills` on every job post, keeping one set per post."""
    return [find_skills(post, dictionary) for post in posts]
