"""Segmentation of a bibliography block into individual citation entries.

The splitter runs a cascade of structural heuristics, from the most reliable
(explicit numeric prefixes) to the weakest (author-name boundaries), and
validates each candidate split before accepting it. A split that produces
mostly non-citation fragments is rejected in favour of the next strategy,
which is what stops a prose document from being shredded into dozens of
meaningless "citations".
"""

from __future__ import annotations

import logging
import re

from papermint.config import SPLIT_VALIDATION_RATIO

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

#: A surname, allowing particles, hyphens, apostrophes and Mc/Mac prefixes.
_SURNAME = (
    r"(?:d[eu]l?\s+|de\s+la\s+|van\s+der\s+|van\s+den\s+|van\s+|von\s+|der\s+|"
    r"la\s+|le\s+|ter\s+|ten\s+|bin\s+|al-)?"
    r"(?:[A-Z][\w'-]+|[A-Z]{2,})"
    r"(?:[-\s][A-Z][\w'-]+)?"
)

#: A line that opens a new entry: "Smith, J.", "O'Brien, Kate", "VAN DYKE, A."
_AUTHOR_BOUNDARY = re.compile(rf"^{_SURNAME},\s+(?:[A-Z]\.|[A-Z][a-z]+|[A-Z]\b)")

#: An explicit entry index at the start of a line.
_NUMBERED_PREFIX = re.compile(r"(?m)(^[ \t]*(?:\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}\.)\s+)")

#: A blank line, used as a paragraph separator.
_BLANK_LINE = re.compile(r"\n\s*\n")

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_DOI = re.compile(r"10\.\d{4,9}/[^\s]+")
_AUTHOR_INITIAL = re.compile(r"[A-Z][a-z]+,\s+[A-Z]")
_BRACKET_INDEX = re.compile(r"^\s*\[\d+\]")
_LOCATOR = re.compile(r"vol\.\s*\d+|pp?\.\s*\d+|\d+\s*\(\d+\)", re.IGNORECASE)

#: Fragments this short cannot be a standalone entry.
_MIN_ENTRY_CHARS = 10


def _looks_like_citation(text: str) -> bool:
    """Check if a text block looks like it could be a citation.

    Args:
        text: A candidate segment.

    Returns:
        True if the text contains at least one bibliographic indicator.
    """
    text = text.strip()
    if not text or len(text) < _MIN_ENTRY_CHARS:
        return False
    indicators = (
        _YEAR.search(text),
        _DOI.search(text),
        _AUTHOR_INITIAL.search(text),
        _BRACKET_INDEX.search(text),
        _LOCATOR.search(text),
    )
    return any(indicators)


def _citation_ratio(segments: list[str]) -> float:
    """Compute the share of segments that look like citations.

    Args:
        segments: Candidate entries.

    Returns:
        A ratio between 0.0 and 1.0.
    """
    if not segments:
        return 0.0
    return sum(1 for s in segments if _looks_like_citation(s)) / len(segments)


def _merge_continuations(segments: list[str]) -> list[str]:
    """Fold obvious continuation fragments back into the preceding entry.

    A segment that opens in lower case, or that is too short to stand alone,
    is almost always the tail of the entry above it rather than a new one.

    The exception is a surname particle. Entries by "van der Berg", "de la
    Cruz" or "von Neumann" open in lower case yet are complete entries, so a
    segment matching the author-boundary pattern is never merged away.

    Args:
        segments: Candidate entries in document order.

    Returns:
        The merged list, never empty when the input was non-empty.
    """
    merged: list[str] = []
    for segment in segments:
        stripped = segment.strip()
        if not stripped:
            continue
        if _AUTHOR_BOUNDARY.match(stripped):
            merged.append(stripped)
            continue
        starts_lower = stripped[0].islower()
        too_short = len(stripped) < _MIN_ENTRY_CHARS
        if merged and (starts_lower or too_short):
            merged[-1] = f"{merged[-1]} {stripped}".strip()
        else:
            merged.append(stripped)
    return merged


def _split_by_numbered_prefixes(text: str) -> list[str]:
    """Split citations by numbered prefixes such as ``[1]``, ``1.`` or ``(1)``.

    Args:
        text: The bibliography block.

    Returns:
        The segmented entries, prefix included.
    """
    parts = _NUMBERED_PREFIX.split(text)

    citations = []
    for i in range(1, len(parts), 2):
        prefix = parts[i]
        cit_text = parts[i + 1] if i + 1 < len(parts) else ""
        citations.append((prefix + cit_text).strip())

    return [c for c in citations if c]


def _split_by_blank_lines(text: str) -> list[str]:
    """Split citations on blank lines.

    Args:
        text: The bibliography block.

    Returns:
        The segmented entries.
    """
    return [p.strip() for p in _BLANK_LINE.split(text) if p.strip()]


def _split_by_hanging_indent(text: str) -> list[str]:
    """Split citations on the hanging-indent convention.

    An unindented line starts a new entry; indented lines continue it.

    Args:
        text: The bibliography block.

    Returns:
        The segmented entries.
    """
    citations: list[str] = []
    current: list[str] = []

    for line in text.split("\n"):
        if not line.strip():
            continue
        if line == line.lstrip() and current:
            citations.append("\n".join(current))
            current = [line.strip()]
        else:
            current.append(line.strip())

    if current:
        citations.append("\n".join(current))

    return citations


def _split_by_author_boundary(text: str) -> list[str]:
    """Split citations at lines that begin with an author surname.

    Blank lines are absorbed into the current entry so that an annotated
    bibliography keeps its citation header and its annotation together as a
    single unit.

    Args:
        text: The bibliography block.

    Returns:
        The segmented entries.
    """
    citations: list[str] = []
    current: list[str] = []

    for line in text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if _AUTHOR_BOUNDARY.match(line_stripped) and current:
            citations.append("\n".join(current))
            current = [line_stripped]
        else:
            current.append(line_stripped)

    if current:
        citations.append("\n".join(current))

    return citations


def _accept(segments: list[str], *, threshold: float = SPLIT_VALIDATION_RATIO) -> list[str] | None:
    """Validate a candidate split and clean it up.

    Args:
        segments: The raw segments produced by a strategy.
        threshold: Minimum share of segments that must look like citations.

    Returns:
        The cleaned segments, or None when the split should be rejected.
    """
    merged = _merge_continuations(segments)
    if len(merged) <= 1:
        return None
    if _citation_ratio(merged) < threshold:
        return None
    return merged


def split_citations(text: str) -> list[str]:
    """Split bibliography text into individual citations.

    The heuristics are tried in descending order of reliability, and each
    candidate split must pass a validation check before it is accepted:

    1. Numbered prefixes: ``[1]``, ``1.``, ``(1)``
    2. Blank-line separation
    3. Hanging indent
    4. Author-name boundaries
    5. Fallback: treat the whole block as a single entry

    Args:
        text: The bibliography text block.

    Returns:
        A list of individual citation strings. Never empty for non-empty
        input.
    """
    if not text.strip():
        return []

    strategies: list[tuple[str, list[str]]] = []

    if _NUMBERED_PREFIX.search(text):
        strategies.append(("numbered prefix", _split_by_numbered_prefixes(text)))

    if _BLANK_LINE.search(text):
        strategies.append(("blank line", _split_by_blank_lines(text)))

    lines = text.split("\n")
    if any(line.strip() and line != line.lstrip() for line in lines):
        strategies.append(("hanging indent", _split_by_hanging_indent(text)))

    author_lines = sum(1 for line in lines if line.strip() and _AUTHOR_BOUNDARY.match(line.strip()))
    if author_lines > 1:
        strategies.append(("author boundary", _split_by_author_boundary(text)))

    for name, segments in strategies:
        accepted = _accept(segments)
        if accepted is not None:
            logger.debug("Split %d entries using the %s strategy", len(accepted), name)
            return accepted

    logger.debug("No split strategy matched; treating the block as one entry")
    return [text.strip()]


__all__ = ["split_citations"]
