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

Two clean-ups make real copy-pasted posts readable:

  * bullets drawn with emoji or symbols ("\u2705 Python \u2705 SQL", common on
    LinkedIn) are turned into line breaks, so each bullet is its own line;
  * a skill that is also a field of study (`degree_subject` in the
    dictionary, e.g. Statistics) is not counted in a sentence about a degree:
    "Laurea in Statistica o affini" asks for a degree, not for the skill.

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
    r"responsibilities|responsabilita(?:\s+principali)?|attivita(?:\s+principali)?|mansioni|"
    r"what\s+you(?:'ll|\s+will)\s+be\s+doing|cosa\s+farai|"
    r"key\s+skills|skills|about\s+you|chi\s+cerchiamo)\b"
)

# Symbols and emoji used as bullets in copy-pasted posts (\u2022 \u25aa \u25b6 \u2713 \u2705 \U0001F539 ...).
# Each one is replaced by a line break before reading the post line by line.
_BULLET_SYMBOLS = re.compile(
    "[\u2022\u2023\u2043\u2219\u25aa\u25ab\u25b6\u25ba\u25cf\u25e6\u2605\u2611"
    "\u2713\u2714\u2705\u27a1\u27a4\u2b50\U0001F300-\U0001FAFF]\ufe0f?"
)

# Words that make a clause about education ("Laurea in ...", "Degree in ...").
_EDUCATION = re.compile(
    r"(?i)(?<![\w&])(?:laurea|laureat[oaie]|degree|bachelor'?s?|master'?s|msc|bsc|phd|"
    r"dottorato|diploma|corso\s+di\s+studi)(?![\w&])"
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


def split_lines(text: str) -> list[str]:
    """Lines of `text`, with emoji/symbol bullets turned into line breaks."""
    return _BULLET_SYMBOLS.sub("\n", text).splitlines()


def find_skill_mentions(
    text: str, dictionary: SkillDictionary, ignore_degree_subjects: bool = False
) -> dict[str, SkillMention]:
    """Find every skill in `text`, with its priority and an example snippet.

    The text is read line by line (to follow the section headers) and clause
    by clause (to apply markers like "is a plus" only where they belong).
    With `ignore_degree_subjects` (used for job posts, not for the CV), a
    `degree_subject` skill is skipped in clauses about a degree.
    """
    found = find_skills(text, dictionary)
    if not found:
        return {}
    skills: list[Skill] = [s for s in dictionary.skills if s.name in found]

    mentions: dict[str, SkillMention] = {}
    seen: set[str] = set()  # skills matched in at least one clause, even if skipped
    section = REQUIRED
    for line in split_lines(text):
        normalized_line = normalize_text(line)
        if not normalized_line:
            continue
        header = _header_kind(normalized_line, dictionary)
        # "Nice to have:" alone opens a nice-to-have section; "Nice to have: X, Y"
        # only concerns its own line (the marker in the clause handles it).
        inline_content = normalized_line.partition(":")[2].strip()
        if header == REQUIRED or (header == NICE_TO_HAVE and not inline_content):
            section = header

        for clause in _CLAUSE_SPLIT.split(line):
            normalized_clause = normalize_text(clause)
            if not normalized_clause:
                continue
            for skill in skills:
                spans = skill.spans(normalized_clause)
                if not spans:
                    continue
                seen.add(skill.name)
                if (
                    ignore_degree_subjects
                    and skill.degree_subject
                    and _EDUCATION.search(normalized_clause)
                ):
                    continue
                priorities = {_mention_priority(normalized_clause, s, section) for s in spans}
                priority = REQUIRED if REQUIRED in priorities else NICE_TO_HAVE
                previous = mentions.get(skill.name)
                # Keep the first mention, unless a later one upgrades it to required.
                if previous is None or (previous.priority != REQUIRED and priority == REQUIRED):
                    mentions[skill.name] = SkillMention(skill.name, priority, _shorten(clause))

    # A phrase broken across two lines is found in the whole text but in no
    # single clause: count it as required, without a snippet.
    for name in found - seen:
        mentions[name] = SkillMention(name, REQUIRED, "")
    return mentions


# Generic headings that job boards put at the top of a post (LinkedIn's
# "About the job", "Informazioni sull'offerta di lavoro"...): skipped when
# choosing a title for the post.
_GENERIC_HEADING = re.compile(
    r"(?i)^(?:about\s+the\s+(?:job|role|company)|about\s+us|job\s+description|the\s+role|"
    r"overview|informazioni\s+sull'offerta(?:\s+di\s+lavoro)?|descrizione\s+(?:del\s+ruolo|"
    r"dell'offerta|della\s+posizione)|il\s+ruolo|chi\s+siamo|cosa\s+farai|what\s+you'll\s+do)\W*$"
)
_TITLE_LENGTH = 60


def post_title(post: str, number: int) -> str:
    """'Post #2 · Data Analyst - Acme' from the first meaningful line of a post."""
    lines = (normalize_text(line) for line in split_lines(post))
    title = next((line for line in lines if line and not _GENERIC_HEADING.match(line)), "")
    if len(title) > _TITLE_LENGTH:
        title = title[: _TITLE_LENGTH - 1].rstrip() + "\u2026"
    return f"Post #{number} · {title}" if title else f"Post #{number}"


def find_skills_in_posts(
    posts: list[str], dictionary: SkillDictionary
) -> list[dict[str, SkillMention]]:
    """Run `find_skill_mentions` on every job post, keeping one dict per post."""
    return [find_skill_mentions(post, dictionary, ignore_degree_subjects=True) for post in posts]
