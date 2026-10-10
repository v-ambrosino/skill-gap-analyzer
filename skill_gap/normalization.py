"""Text normalisation shared by the dictionary loader and the extractor.

Job posts and CVs come from copy-paste and PDFs, so the same word can be
written in many ways: "visualizzazione", "Visualizzazione", a non-breaking
space instead of a normal one, a typographic apostrophe, a PDF ligature...
Both the dictionary phrases and the input texts go through the same function,
so they always compare like with like.
"""

from __future__ import annotations

import re
import unicodedata

# Typographic characters that PDFs and word processors like to insert.
_PUNCTUATION_MAP = str.maketrans(
    {
        "‘": "'",  # left single quote
        "’": "'",  # right single quote / apostrophe
        "“": '"',
        "”": '"',
        "‐": "-",  # hyphen
        "‑": "-",  # non-breaking hyphen
        "‒": "-",
        "–": "-",  # en dash
        "—": "-",  # em dash
        " ": " ",  # non-breaking space
    }
)

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Return `text` without accents, with plain punctuation and single spaces.

    The original casing is KEPT on purpose: some skills (e.g. "R", "SAS") are
    matched case-sensitively. Case-insensitive matching is done with the
    re.IGNORECASE flag instead of lower-casing the text.

    Examples:
        "Capacità  analitiche" -> "Capacita analitiche"
        "Power‑BI"        -> "Power-BI"
    """
    # NFKD splits "à" into "a" + combining accent, and expands ligatures
    # such as "ﬁ" into "fi". We then drop the combining marks.
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    plain = without_accents.translate(_PUNCTUATION_MAP)
    # Line breaks from PDFs often split phrases ("machine\nlearning"),
    # so every run of whitespace becomes one space.
    return _WHITESPACE.sub(" ", plain).strip()
