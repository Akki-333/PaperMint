"""Text normalisation utilities applied between extraction and parsing.

Raw text pulled out of a PDF is rarely clean: it carries typographic
ligatures, soft hyphens, mid-word line breaks, running headers, bare page
numbers and inconsistent dash characters. Feeding that directly into the
citation parsers produces fields such as ``"bibliomet- rics"`` which read as
broken output in the UI.

Every function in this module is pure and framework agnostic.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Character-level cleanup tables
# ---------------------------------------------------------------------------

#: Characters that carry no semantic weight and only corrupt regex matching.
_ZERO_WIDTH = dict.fromkeys(
    [
        0x00AD,  # soft hyphen
        0x200B,  # zero width space
        0x200C,  # zero width non-joiner
        0x200D,  # zero width joiner
        0x200E,  # left-to-right mark
        0x200F,  # right-to-left mark
        0xFEFF,  # byte order mark
    ]
)

#: Typographic characters mapped to their ASCII equivalents.
_PUNCTUATION_MAP = {
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    "′": "'",
    "″": '"',
    "‐": "-",
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "―": "-",
    "−": "-",
    " ": " ",
    " ": " ",
    " ": " ",
    " ": " ",
    "…": "...",
}

_PUNCTUATION_TABLE = str.maketrans(_PUNCTUATION_MAP)

#: A word broken across a line break, for example "bibliomet-\nrics".
_HYPHEN_LINEBREAK = re.compile(r"(?<=[a-z])-[ \t]*\n[ \t]*(?=[a-z])")

#: A bare page number occupying an entire line, optionally decorated.
_PAGE_NUMBER_LINE = re.compile(
    r"^\s*[-\[(]?\s*(?:page\s+)?\d{1,4}\s*(?:/\s*\d{1,4}\s*)?[-\])]?\s*$",
    re.IGNORECASE,
)

#: Three or more consecutive blank lines.
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")

#: Runs of horizontal whitespace.
_HORIZONTAL_RUNS = re.compile(r"[ \t]{2,}")

#: Space wrongly inserted before closing punctuation.
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)\]])")

#: Missing space after a sentence-ending period followed by a capital.
_MISSING_SPACE_AFTER_PERIOD = re.compile(r"(?<=[a-z])\.(?=[A-Z][a-z])")


def strip_control_characters(text: str) -> str:
    """Remove zero-width and non-printable control characters.

    Args:
        text: Arbitrary extracted text.

    Returns:
        The text with invisible characters removed. Tabs, newlines and
        carriage returns are preserved.
    """
    if not text:
        return ""
    text = text.translate(_ZERO_WIDTH)
    return "".join(ch for ch in text if ch in "\n\r\t" or unicodedata.category(ch) != "Cc")


def normalize_unicode(text: str) -> str:
    """Fold typographic ligatures and unify punctuation to ASCII.

    ``NFKC`` decomposes ligatures such as the ``fi`` glyph into two characters
    and normalises full-width forms. Curly quotes and the six different dash
    characters found in academic PDFs are then mapped onto ASCII equivalents.

    Args:
        text: Arbitrary extracted text.

    Returns:
        The normalised text.
    """
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).translate(_PUNCTUATION_TABLE)


def dehyphenate(text: str) -> str:
    """Rejoin words that a PDF line break split with a hyphen.

    Only lowercase-to-lowercase breaks are rejoined, so genuine compound words
    at a line end and numeric ranges are left untouched.

    Args:
        text: Text whose lines may contain hyphenated word breaks.

    Returns:
        The text with broken words rejoined.
    """
    if not text:
        return ""
    return _HYPHEN_LINEBREAK.sub("", text)


def _repeated_boilerplate(lines: list[str], *, min_repeats: int = 3) -> set[str]:
    """Identify short lines that repeat often enough to be running headers.

    Args:
        lines: The document's non-empty lines, already stripped.
        min_repeats: How many occurrences qualify a line as boilerplate.

    Returns:
        The set of lines considered running headers or footers.
    """
    candidates = Counter(
        line for line in lines if 3 <= len(line) <= 90 and not line.endswith((".", ";"))
    )
    threshold = max(min_repeats, len(lines) // 40)
    return {line for line, count in candidates.items() if count >= threshold}


def strip_running_furniture(text: str) -> str:
    """Drop bare page numbers and repeated running headers or footers.

    Args:
        text: Multi-page document text.

    Returns:
        The text with page furniture removed.
    """
    if not text:
        return ""

    raw_lines = text.split("\n")
    stripped = [line.strip() for line in raw_lines]
    boilerplate = _repeated_boilerplate([s for s in stripped if s])

    kept: list[str] = []
    for original, bare in zip(raw_lines, stripped, strict=True):
        if bare and _PAGE_NUMBER_LINE.match(bare):
            continue
        if bare and bare in boilerplate:
            continue
        kept.append(original)
    return "\n".join(kept)


def collapse_whitespace(text: str) -> str:
    """Normalise runs of spaces and blank lines without destroying structure.

    Leading indentation is preserved because the citation splitter relies on
    hanging indents to find entry boundaries.

    Args:
        text: Text to tidy.

    Returns:
        The tidied text.
    """
    if not text:
        return ""

    lines = []
    for line in text.split("\n"):
        indent_len = len(line) - len(line.lstrip(" \t"))
        indent = " " * min(indent_len, 8)
        body = _HORIZONTAL_RUNS.sub(" ", line.strip())
        lines.append(f"{indent}{body}" if body else "")
    return _EXCESS_BLANK_LINES.sub("\n\n", "\n".join(lines)).strip("\n")


def normalize_document(text: str, *, strip_furniture: bool = True) -> str:
    """Run the full normalisation pipeline over an extracted document.

    Args:
        text: The raw text produced by an extractor.
        strip_furniture: Whether to remove page numbers and running headers.
            Disable for short single-page inputs where repetition is
            meaningful.

    Returns:
        Clean text suitable for bibliography detection and parsing.
    """
    if not text or not text.strip():
        return ""

    text = strip_control_characters(text)
    text = normalize_unicode(text)
    text = dehyphenate(text)
    if strip_furniture:
        text = strip_running_furniture(text)
    return collapse_whitespace(text)


def normalize_field(value: str, *, max_length: int = 400) -> str:
    """Tidy a single extracted bibliographic field for display and export.

    Strips stray leading and trailing punctuation, repairs spacing around
    punctuation marks, collapses internal whitespace and removes the dangling
    connector words that regex extraction commonly leaves behind.

    Args:
        value: The raw extracted field value.
        max_length: Hard cap applied after cleaning.

    Returns:
        The cleaned field, or an empty string if nothing survives.
    """
    if not value:
        return ""

    value = normalize_unicode(strip_control_characters(value))
    value = value.replace("\n", " ")
    value = _HORIZONTAL_RUNS.sub(" ", value).strip()
    value = _SPACE_BEFORE_PUNCT.sub(r"\1", value)
    value = _MISSING_SPACE_AFTER_PERIOD.sub(". ", value)

    # Drop leading list markers, connectors and orphaned punctuation.
    value = re.sub(r"^(?:\[\d+\]|\(\d+\)|\d+\.)\s*", "", value)
    value = re.sub(r"^(?:in|In|and|And|&|,|\.|;|:|-)\s+", "", value)
    value = value.strip(" ,;:-")

    # Remove an unmatched trailing quote or an orphaned opening bracket.
    if value.count('"') % 2 == 1:
        value = value.replace('"', "")
    value = re.sub(r"\s*[([]\s*$", "", value)

    value = value.strip()
    if len(value) > max_length:
        value = value[:max_length].rsplit(" ", 1)[0].rstrip(" ,;:-") + "..."
    return value


def sentence_count(text: str) -> int:
    """Count sentences without inflating the total on initials and DOIs.

    A naive ``text.count(".")`` reports dozens of extra sentences for a
    bibliography full of author initials, which then surfaces in the UI as an
    obviously wrong statistic.

    Args:
        text: The text to measure.

    Returns:
        The estimated number of sentences.
    """
    if not text or not text.strip():
        return 0
    probe = re.sub(r"\b[A-Z]\.", "", text)  # author initials
    probe = re.sub(r"10\.\d{4,9}/\S+", "", probe)  # DOIs
    probe = re.sub(r"\b(?:et al|vol|no|pp|ed|eds|cf|i\.e|e\.g)\.", "", probe, flags=re.IGNORECASE)
    return len(re.findall(r"[.!?]+(?=\s|$)", probe))


def word_count(text: str) -> int:
    """Count whitespace-delimited word tokens.

    Args:
        text: The text to measure.

    Returns:
        The number of word tokens.
    """
    return len(text.split()) if text else 0


__all__ = [
    "collapse_whitespace",
    "dehyphenate",
    "normalize_document",
    "normalize_field",
    "normalize_unicode",
    "sentence_count",
    "strip_control_characters",
    "strip_running_furniture",
    "word_count",
]
