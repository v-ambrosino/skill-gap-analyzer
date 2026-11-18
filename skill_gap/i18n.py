"""Interface languages: English (the source text) and Italian.

The code wraps every sentence shown to the user in `t("English text")`. With
English selected the text is returned as it is; with another language it is
looked up in that language's table (see `translations.py`), falling back to
English when a sentence has no translation yet. A test checks that every
sentence used by the app has an Italian translation.

The current language lives in a context variable, so two visitors of the same
server can read the app in different languages at the same time.

Skill names, categories and role names come from the dictionaries and are not
translated.
"""

from __future__ import annotations

from contextvars import ContextVar

from skill_gap.translations import TRANSLATIONS

DEFAULT_LANGUAGE = "en"
# Code -> name shown in the language switch.
LANGUAGES = {"en": "English", "it": "Italiano"}

_language: ContextVar[str] = ContextVar("skill_gap_language", default=DEFAULT_LANGUAGE)


def set_language(code: str | None) -> str:
    """Select the language for the current run; unknown codes fall back to English."""
    code = code if code in LANGUAGES else DEFAULT_LANGUAGE
    _language.set(code)
    return code


def get_language() -> str:
    return _language.get()


def language_from_locale(locale: str | None) -> str:
    """'it-IT' -> 'it'; anything that is not a supported language -> English."""
    code = (locale or "").split("-")[0].split("_")[0].lower()
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def t(text: str, **values) -> str:
    """`text` in the current language, with `{placeholders}` filled from `values`."""
    translated = TRANSLATIONS.get(get_language(), {}).get(text, text)
    return translated.format(**values) if values else translated


def plural(count: int, one: str, many: str) -> str:
    """`one` or `many` (both translated) for `count`, which fills `{n}`."""
    return t(one if count == 1 else many, n=count)
