"""Find dictionary skills in free text (a CV or a job post).

The approach is deliberately simple and explainable: no AI, no external API.
A skill is "found" when at least one of its synonyms appears in the text as a
whole word. Each skill counts at most once per document, so the analysis
measures "in how many job posts is this skill requested", which is more
robust than counting raw mentions (a post repeating "Excel" five times is
still one employer asking for Excel).

For job posts we also look at the CONTEXT of each mention, to tell apart
skills that are required from skills that are only "nice to have":

  * section headers: everything under "Nice to have:" / "Bonus:" /
    "Titoli preferenziali:" is nice to have, until a header such as
    "Requirements:" / "Requisiti:" / "Responsibilities:" starts a new section;
  * markers in the same clause: "Python is a plus", "gradita la conoscenza
    di Tableau", "costituisce titolo preferenziale la conoscenza di R";
  * markers inside brackets apply only to the brackets:
    "SQL (BigQuery preferred)" -> SQL required, BigQuery nice to have.

A skill is "required" in a post if at least one of its mentions is in a
required context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skill_gap.normalization import normalize_text
from skill_gap.skills_dictionary import Skill, SkillDictionary

REQUIRED = "required"
NICE_TO_HAVE = "nice_to_have"

# A separator line made only of three or more dashes, e.g. "---".
_POST_SEPARATOR = re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE)

# Words that turn a requirement into a "nice to have". They are matched on the
# normalised text, so accents are already removed ("gradita", "preferenziale").
_NICE_MARKERS = re.compile(
    r"(?i)(?<![\w&])(?:"
    r"nice[\s-]*to[\s-]*haves?|bonus(?:\s+points?)?|preferred|preferabl[ey]|"
    r"desirable|desired|ideally|advantageous|an\s+advantage|"
    r"(?:is|are|would\s+be|will\s+be|as|a|un|e|sara|rappresenta|costituisce|"
    r"costituira|considerato|considerata)\s+(?:a\s+|un\s+)?(?:big\s+|grande\s+|forte\s+)?plus|"
    r"gradit[aoie]|preferenzial[ei]|preferibil\w*|apprezzat[aoie]|"
    r"optional|facoltativ[aoie]"
    r")(?![\w&])"
)

# Section headers that (re)start a required section. Matched at the start of
# a short line, so "Requirements:" counts but "requirements gathering" does not.
_REQUIRED_HEADER = re.compile(
    r"(?i)^(?:requirements?|requisiti(?:\s+richiesti)?|must[\s-]*haves?|"
    r"what\s+(?:we're|we\s+are)\s+looking\s+for|what\s+you(?:'ll|\s+will)?\s+(?:bring|need|do)|"
    r"your\s+profile|your\s+responsibilities|il\s+tuo\s+profilo|profilo(?:\s+ricercato)?|"
    r"qualifications?|required|essential|competenze(?:\s+richieste)?|cosa\s+cerchiamo|"
    r"responsibilities|responsabilita|attivita(?:\s+principali)?|mansioni|"
    r"key\s+skills|skills|about\s+you|chi\s+cerchiamo)\b"
)

# Bullets and numbering at the start of a line.
_BULLET = re.compile(r"^[\s\-\*•·>\d.)]+")
# Clause boundaries inside a line: ";" or the end of a sentence.
_CLAUSE_SPLIT = re.compile(r";|(?<=[.!?])\s+(?=[A-Z])")
_PARENTHESES = re.compile(r"\([^()]*\)")
_MAX_HEADER_WORDS = 6
_SNIPPET_LENGTH = 160


@dataclass(frozen=True)
class SkillMention:
    """Where a skill was found in a document, and whether it is required."""

    skill: str
    priority: str  # REQUIRED or NICE_TO_HAVE
    snippet: str  # the clause of the original text that mentions the skill


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


def _header_kind(normalized_line: str, dictionary: SkillDictionary) -> str | None:
    """Return REQUIRED / NICE_TO_HAVE if the line is a section header, else None.

    A header is short text before a colon ("Nice to have: ...") or a short
    line on its own ("Requisiti"). The part before the colon must not mention
    a skill itself, so "SQL (BigQuery preferred)" is never taken as a header.
    """
    line = _BULLET.sub("", normalized_line).strip()
    head, has_colon, _ = line.partition(":")
    head = head.strip(" .!-")
    if not head or len(head.split()) > _MAX_HEADER_WORDS:
        return None
    if not has_colon and len(line.split()) > _MAX_HEADER_WORDS:
        return None
    if any(skill.is_in(head) for skill in dictionary.skills):
        return None
    if _NICE_MARKERS.search(head):
        return NICE_TO_HAVE
    if _REQUIRED_HEADER.match(head):
        return REQUIRED
    return None


def _mention_priority(
    normalized_clause: str, span: tuple[int, int], section: str
) -> str:
    """Priority of one match, given its clause and the current section."""
    # Text of the clause with the bracketed parts removed: a marker here
    # ("Python is a plus") applies to the whole clause.
    outside_brackets = _PARENTHESES.sub(" ", normalized_clause)
    if _NICE_MARKERS.search(outside_brackets):
        return NICE_TO_HAVE
    # A marker inside brackets applies only to what is inside those brackets.
    for bracket in _PARENTHESES.finditer(normalized_clause):
        start, end = bracket.span()
        if start <= span[0] and span[1] <= end and _NICE_MARKERS.search(bracket.group()):
            return NICE_TO_HAVE
    return section


def _shorten(text: str) -> str:
    text = " ".join(text.split()).strip(" -•*")
    if len(text) <= _SNIPPET_LENGTH:
        return text
    return text[: _SNIPPET_LENGTH - 1].rstrip() + "…"


def find_skill_mentions(text: str, dictionary: SkillDictionary) -> dict[str, SkillMention]:
    """Find every skill in `text`, with its priority and an example snippet.

    The text is read line by line (to follow the section headers) and clause
    by clause (to apply markers like "is a plus" only where they belong).
    """
    found = find_skills(text, dictionary)
    if not found:
        return {}
    skills: list[Skill] = [s for s in dictionary.skills if s.name in found]

    mentions: dict[str, SkillMention] = {}
    section = REQUIRED
    for line in text.splitlines():
        normalized_line = normalize_text(line)
        if not normalized_line:
            continue
        header = _header_kind(normalized_line, dictionary)
        if header is not None:
            section = header

        for clause in _CLAUSE_SPLIT.split(line):
            normalized_clause = normalize_text(clause)
            if not normalized_clause:
                continue
            for skill in skills:
                spans = skill.spans(normalized_clause)
                if not spans:
                    continue
                priorities = {_mention_priority(normalized_clause, s, section) for s in spans}
                priority = REQUIRED if REQUIRED in priorities else NICE_TO_HAVE
                previous = mentions.get(skill.name)
                # Keep the first mention, unless a later one upgrades it to required.
                if previous is None or (previous.priority != REQUIRED and priority == REQUIRED):
                    mentions[skill.name] = SkillMention(skill.name, priority, _shorten(clause))

    # A phrase broken across two lines is found in the whole text but in no
    # single clause: count it as required, without a snippet.
    for name in found - mentions.keys():
        mentions[name] = SkillMention(name, REQUIRED, "")
    return mentions


def find_skills_in_posts(
    posts: list[str], dictionary: SkillDictionary
) -> list[dict[str, SkillMention]]:
    """Run `find_skill_mentions` on every job post, keeping one dict per post."""
    return [find_skill_mentions(post, dictionary) for post in posts]
