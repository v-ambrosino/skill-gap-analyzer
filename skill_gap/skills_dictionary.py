"""Load the YAML skill dictionary and compile it into regular expressions.

Each dictionary is plain data (see data/dictionaries/) so it can be edited
without touching the code. This module:
  1. reads and validates the file (plus the files it `include`s), with clear
     error messages;
  2. turns every synonym into a whole-word regular expression;
  3. returns an immutable SkillDictionary used by the extractor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from skill_gap.normalization import normalize_text

DICTIONARIES_DIR = Path(__file__).resolve().parent.parent / "data" / "dictionaries"
DEFAULT_DICTIONARY_PATH = DICTIONARIES_DIR / "data_analytics.yaml"

# A match must not be glued to a letter, digit, underscore or "&" on either
# side. This is a stricter version of regex "\b": it stops "sql" matching
# inside "NoSQL"/"MySQL", and "R" matching inside "R&D".
_BOUNDARY_BEFORE = r"(?<![\w&])"
_BOUNDARY_AFTER = r"(?![\w&])"

# Inside a phrase, spaces and hyphens are interchangeable and optional:
# "power bi" matches "Power BI", "Power-BI" and "PowerBI".
_TOKEN_JOINER = r"[\s\-]*"
_TOKEN_SPLITTER = re.compile(r"[\s\-]+")

# Phrases at least this long also match their plural ("dashboard" ->
# "dashboards", "process" -> "processes"). Short acronyms are excluded so
# that e.g. "sas" never turns into "sass".
_MIN_LENGTH_FOR_PLURAL = 4


class DictionaryError(ValueError):
    """Raised when the skill dictionary file is missing or malformed."""


@dataclass(frozen=True)
class Skill:
    """One skill and the compiled regular expressions that recognise it."""

    name: str
    category: str
    patterns: tuple[re.Pattern, ...]

    def is_in(self, normalized_text: str) -> bool:
        """True if at least one pattern matches the (normalised) text."""
        return any(pattern.search(normalized_text) for pattern in self.patterns)

    def spans(self, normalized_text: str) -> list[tuple[int, int]]:
        """Start/end positions of every match, used to look at the context."""
        return [m.span() for pattern in self.patterns for m in pattern.finditer(normalized_text)]


@dataclass(frozen=True)
class SkillDictionary:
    """All the skills of one domain, plus the ordered list of categories."""

    domain: str
    categories: tuple[str, ...]
    skills: tuple[Skill, ...]
    description: str = ""

    def category_of(self, skill_name: str) -> str:
        for skill in self.skills:
            if skill.name == skill_name:
                return skill.category
        raise KeyError(skill_name)


def synonym_to_regex(phrase: str, case_sensitive: bool = False) -> re.Pattern:
    """Compile a dictionary phrase into a whole-word regular expression.

    >>> bool(synonym_to_regex("power bi").search("Strong PowerBI skills"))
    True
    >>> bool(synonym_to_regex("sql").search("NoSQL databases"))
    False
    """
    normalized = normalize_text(phrase)
    tokens = [re.escape(token) for token in _TOKEN_SPLITTER.split(normalized) if token]
    if not tokens:
        raise DictionaryError(f"Empty synonym: {phrase!r}")

    body = _TOKEN_JOINER.join(tokens)
    if (
        not case_sensitive
        and len(normalized) >= _MIN_LENGTH_FOR_PLURAL
        and normalized[-1].isalpha()
    ):
        body += "(?:e?s)?"

    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(_BOUNDARY_BEFORE + body + _BOUNDARY_AFTER, flags)


def _as_list(value, field: str, skill_name: str) -> list[str]:
    """Accept a missing field, a single string or a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise DictionaryError(f"Skill {skill_name!r}: '{field}' must be a list of strings.")


def parse_dictionary(data: dict) -> SkillDictionary:
    """Validate the raw YAML content and build a SkillDictionary."""
    if not isinstance(data, dict) or "skills" not in data:
        raise DictionaryError("The dictionary must be a mapping with a 'skills' list.")

    categories = tuple(data.get("categories") or [])
    if not categories:
        raise DictionaryError("The dictionary must declare a non-empty 'categories' list.")

    skills: list[Skill] = []
    seen_names: set[str] = set()
    # Maps a normalised, lower-cased synonym to the skill that owns it, so the
    # same phrase cannot silently count for two different skills.
    synonym_owner: dict[str, str] = {}

    for index, entry in enumerate(data["skills"], start=1):
        if not isinstance(entry, dict):
            raise DictionaryError(f"Skill #{index} is not a mapping.")
        name = entry.get("name")
        category = entry.get("category")
        if not name or not isinstance(name, str):
            raise DictionaryError(f"Skill #{index} has no 'name'.")
        if name in seen_names:
            raise DictionaryError(f"Duplicate skill name: {name!r}.")
        if category not in categories:
            raise DictionaryError(
                f"Skill {name!r}: unknown category {category!r}. "
                f"Allowed: {', '.join(categories)}."
            )
        seen_names.add(name)

        synonyms = _as_list(entry.get("synonyms"), "synonyms", name)
        case_sensitive = _as_list(
            entry.get("case_sensitive_synonyms"), "case_sensitive_synonyms", name
        )
        raw_patterns = _as_list(entry.get("patterns"), "patterns", name)
        if not (synonyms or case_sensitive or raw_patterns):
            raise DictionaryError(f"Skill {name!r} has no synonyms or patterns.")

        for phrase in synonyms + case_sensitive:
            key = normalize_text(phrase).lower()
            owner = synonym_owner.setdefault(key, name)
            if owner != name:
                raise DictionaryError(
                    f"Synonym {phrase!r} is used by both {owner!r} and {name!r}."
                )

        compiled = [synonym_to_regex(p) for p in synonyms]
        compiled += [synonym_to_regex(p, case_sensitive=True) for p in case_sensitive]
        for raw in raw_patterns:
            try:
                compiled.append(re.compile(raw))
            except re.error as exc:
                raise DictionaryError(f"Skill {name!r}: invalid pattern {raw!r} ({exc}).")

        # Different synonyms can compile to the same regex ("crisp-dm" and
        # "crisp dm"): drop the duplicates, keeping the original order.
        unique = tuple({(p.pattern, p.flags): p for p in compiled}.values())
        skills.append(Skill(name=name, category=category, patterns=unique))

    return SkillDictionary(
        domain=str(data.get("domain", "")),
        categories=categories,
        skills=tuple(skills),
        description=str(data.get("description", "")),
    )


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise DictionaryError(f"Dictionary file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        try:
            data = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise DictionaryError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DictionaryError(f"{path} must contain a YAML mapping.")
    return data


def load_dictionary(path: str | Path = DEFAULT_DICTIONARY_PATH) -> SkillDictionary:
    """Read a YAML dictionary from disk and return a validated SkillDictionary.

    The optional `include` key lists other YAML files (relative to this one)
    whose `skills` are appended, e.g. soft skills shared by several roles.
    Included skills are validated like the others: their categories must be
    declared by the including dictionary.
    """
    path = Path(path)
    data = _read_yaml(path)
    skills = list(data.get("skills") or [])
    for included in _as_list(data.get("include"), "include", path.name):
        skills += _read_yaml(path.parent / included).get("skills") or []
    return parse_dictionary({**data, "skills": skills})


def list_dictionaries(folder: str | Path = DICTIONARIES_DIR) -> dict[str, Path]:
    """Map each dictionary's `domain` to its file, default dictionary first.

    Every *.yaml file directly inside `folder` is a role dictionary; files in
    sub-folders (such as shared/) are only meant to be included.
    """
    folder = Path(folder)
    found = {}
    for path in sorted(folder.glob("*.yaml"), key=lambda p: (p != DEFAULT_DICTIONARY_PATH, p.name)):
        domain = str(_read_yaml(path).get("domain") or path.stem)
        found[domain] = path
    return found
