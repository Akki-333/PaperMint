"""Bibliography detection and document characterisation.

Two entry points are exposed:

``detect_bibliography_section``
    The original, string-in string-out helper. Returns the bibliography text
    or an empty string.

``characterize_document``
    The richer entry point used by the orchestration layer. It returns a
    :class:`DetectionOutcome` that also reports *how* the bibliography was
    found, what kind of document this is, and where the narrative body ends,
    so the UI can explain its reasoning instead of silently guessing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from papermint.config import (
    BIBLIOGRAPHY_DENSITY_THRESHOLD,
    BIBLIOGRAPHY_HEADERS,
    FRONT_MATTER_MAX_LINES,
    REFERENCE_ONLY_COVERAGE,
)
from papermint.models import DetectionMethod, DocumentKind

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s]+")
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
_AUTHOR_PATTERN = re.compile(r"[A-Z][a-z]+,?\s+[A-Z]\.")
_AUTHOR_FULL_PATTERN = re.compile(r"^[A-Z][a-zA-Z\s\-']+,?\s+[A-Z][a-zA-Z\s\-']+")
_BRACKET_PATTERN = re.compile(r"^\[\d+\]")
_LOCATOR_PATTERN = re.compile(r"\b(?:vol|no|pp)\.\s*\d+", re.IGNORECASE)
_ARXIV_PATTERN = re.compile(r"\barXiv:\s*\d{4}\.\d{4,5}", re.IGNORECASE)

_BOOK_IMPRINT = re.compile(
    r"\b(?:Press|Publishing|Publishers|Books|Verlag|Co\.|Inc\.|Ltd\.)\b", re.IGNORECASE
)
_BOOK_PAGINATION = re.compile(r"\b\d{1,4}\s*p(?:p)?\.?\b", re.IGNORECASE)
_CONTRIBUTOR_ROLE = re.compile(
    r"\b(?:Illus\.|illustrated|Comp\.|Compiled|Ed\.|Eds\.|Edited|Trans\.|Translated)\s+by\b",
    re.IGNORECASE,
)

#: The closing "Journal Abbrev. Volume, Pages (Year)" of a numbered reference.
#: Recognising it keeps the wrapped second line of an entry from reading as
#: prose, which would otherwise end the backwards scan inside the reference
#: list rather than above it.
_VENUE_PATTERN = re.compile(
    r"[A-Z][A-Za-z.]*\.?\s+\d{1,4},\s*[A-Za-z]?\d[\w-]*\s*\((?:19|20)\d{2}\)"
)

#: Words per line above which a non-bibliographic line counts as real prose
#: rather than the short tail of a wrapped reference.
_PROSE_WORD_FLOOR = 8

#: Pattern detecting document title declarations for bibliographies and catalogs.
_TITLE_PAGE_PATTERN = re.compile(
    r"(?:^|\b)(?:title\s*[:.-]?\s*)?"
    r"(?:an?\s+|the\s+)?"
    r"(?:annotated\s+|selected\s+|classified\s+|comprehensive\s+|curriculum\s+)?"
    r"(?:bibliography|works\s+cited|reference\s+list|literature\s+cited)\b",
    re.IGNORECASE,
)

#: How many consecutive non-citation lines end a density-detected block.
_MAX_PROSE_GAP = 4

#: Minimum words of trailing prose that mark an entry as annotated.
_ANNOTATION_WORD_FLOOR = 40


def _build_header_pattern() -> re.Pattern[str]:
    """Compile the section-heading regex from the configured keywords.

    Matches single-line section headers with optional numeric, part or chapter prefixes,
    such as '7. References', 'PART TWO Annotated Bibliography' or 'References:'.
    """
    headers = "|".join(re.escape(header) for header in BIBLIOGRAPHY_HEADERS)
    prefix = (
        r"(?:(?:\d+\.?|(?:part|chapter|section|appendix)\s+"
        r"(?:one|two|three|four|five|\d+|[ivx]+))\s*[:.-]*)?"
    )
    return re.compile(
        rf"^\s*{prefix}(?:{headers})\s*[:.]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )


def _build_multi_line_header_pattern() -> re.Pattern[str]:
    """Compile a regex for two-line section headers like 'PART TWO\\nAnnotated Bibliography'."""
    headers = "|".join(re.escape(header) for header in BIBLIOGRAPHY_HEADERS)
    return re.compile(
        rf"^\s*(?:part|chapter|section|appendix)\s+(?:one|two|three|four|five|\d+|[ivx]+)\s*\n"
        rf"^\s*(?:{headers})\s*[:.]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )


_HEADER_PATTERN = _build_header_pattern()
_MULTI_LINE_HEADER_PATTERN = _build_multi_line_header_pattern()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DetectionOutcome:
    """What the detector concluded about a document.

    Attributes:
        bibliography_text: The isolated bibliography block, or an empty string.
        body_text: The narrative text with the bibliography removed.
        method: Which strategy located the bibliography.
        kind: How the document as a whole was classified.
        confidence: How strongly the evidence supports the classification.
        notes: Human-readable observations for the UI to surface.
    """

    bibliography_text: str = ""
    body_text: str = ""
    method: DetectionMethod = DetectionMethod.NONE
    kind: DocumentKind = DocumentKind.UNKNOWN
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        """Whether a bibliography block was isolated."""
        return bool(self.bibliography_text.strip())


# ---------------------------------------------------------------------------
# Line-level heuristics
# ---------------------------------------------------------------------------


def _citation_signal(line: str) -> bool:
    """Judge whether a single line carries bibliographic structure.

    A DOI, a bracketed index, a volume locator, book pagination or contributor credit
    is decisive on its own. Author patterns count when paired with a year, imprint,
    or title indicators.

    Args:
        line: One stripped line of text.

    Returns:
        True when the line looks like part of a reference entry.
    """
    if not line:
        return False
    if _DOI_PATTERN.search(line) or _BRACKET_PATTERN.search(line):
        return True
    if _ARXIV_PATTERN.search(line) or _VENUE_PATTERN.search(line):
        return True
    if _LOCATOR_PATTERN.search(line) or _BOOK_PAGINATION.search(line):
        return True
    if _CONTRIBUTOR_ROLE.search(line):
        return True
    if _BOOK_IMPRINT.search(line) and _YEAR_PATTERN.search(line):
        return True
    if _YEAR_PATTERN.search(line) and _AUTHOR_PATTERN.search(line):
        return True
    return bool(
        _AUTHOR_FULL_PATTERN.match(line)
        and (_YEAR_PATTERN.search(line) or ":" in line or '"' in line or "." in line)
    )


def _is_prose(line: str) -> bool:
    """Judge whether a line is narrative text rather than a reference fragment.

    A wrapped reference leaves short tails such as "081406 (2009)." on their own
    line. Those must not be mistaken for body prose, or the backwards scan stops
    inside the reference list.

    Args:
        line: One stripped line of text.

    Returns:
        True when the line reads as a sentence of narrative body text.
    """
    return len(line.split()) >= _PROSE_WORD_FLOOR and not _citation_signal(line)


def _density(lines: list[str]) -> float:
    """Compute the share of lines that look bibliographic.

    Args:
        lines: Stripped, non-empty lines.

    Returns:
        A ratio between 0.0 and 1.0.
    """
    if not lines:
        return 0.0
    return sum(1 for line in lines if _citation_signal(line)) / len(lines)


def _has_bibliographic_density(text: str) -> bool:
    """Check if the text has high bibliographic density.

    Args:
        text: The text to analyze.

    Returns:
        True if the text appears to be a bibliography based on density.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return _density(lines) > BIBLIOGRAPHY_DENSITY_THRESHOLD


def _find_dense_block_start(lines: list[str], search_from: int) -> int:
    """Walk backwards from the end to find where the dense block begins.

    Starting at the last line, the scan extends upwards while reference-like
    lines keep appearing, tolerating short runs of continuation lines. It stops
    at the first sustained run of prose, which is the boundary between the
    narrative body and the reference list.

    Only lines that read as real prose count towards the run. A wrapped
    reference leaves short numeric tails behind, and counting those would end
    the scan inside the reference list.

    Args:
        lines: The document's lines, unstripped.
        search_from: The midpoint of the document, retained so the scan can be
            reported against the region that triggered it.

    Returns:
        The index of the first line of the dense block.
    """
    del search_from  # The prose run alone decides the boundary.

    boundary = len(lines)
    gap = 0
    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if _citation_signal(stripped):
            boundary = index
            gap = 0
            continue
        if not _is_prose(stripped):
            continue
        gap += 1
        # A sustained run of narrative text is the top of the reference list.
        # The previous implementation also required the run to sit above the
        # document midpoint, which made the break unreachable for any paper
        # whose appendix and references filled the bottom half, so an entire
        # appendix was swallowed into the bibliography.
        if gap > _MAX_PROSE_GAP:
            break
    return boundary


def _looks_annotated(text: str) -> bool:
    """Detect an annotated bibliography by its trailing prose paragraphs.

    Args:
        text: The isolated bibliography block.

    Returns:
        True when a meaningful share of entries carry annotation prose.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) < 2:
        return False

    annotated = 0
    for block in blocks:
        block_lines = [line for line in block.split("\n") if line.strip()]
        if len(block_lines) < 2:
            continue
        trailing = " ".join(block_lines[1:])
        if len(trailing.split()) >= _ANNOTATION_WORD_FLOOR and not _citation_signal(
            block_lines[-1].strip()
        ):
            annotated += 1
    return annotated / len(blocks) >= 0.3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def characterize_document(text: str, force_parse: bool = False) -> DetectionOutcome:
    """Classify a document and isolate its bibliography.

    Strategies are applied in descending order of reliability:

    1. An explicit reader override (``force_parse``).
    2. A first line that names the document a bibliography.
    3. A ``References``-style heading on a line of its own.
    4. A backwards density scan over the tail of the document.

    Args:
        text: The full, normalised text of the document.
        force_parse: Treat the entire document as a bibliography.

    Returns:
        A :class:`DetectionOutcome` describing what was found and how.
    """
    if not text or not text.strip():
        return DetectionOutcome(notes=["The document contains no readable text."])

    stripped = text.strip()

    # 1. Reader override.
    if force_parse:
        kind = (
            DocumentKind.ANNOTATED_BIBLIOGRAPHY
            if _looks_annotated(stripped)
            else DocumentKind.BIBLIOGRAPHY
        )
        return DetectionOutcome(
            bibliography_text=stripped,
            body_text="",
            method=DetectionMethod.FORCED,
            kind=kind,
            confidence=1.0,
            notes=["Every line was parsed as a citation because you asked for it."],
        )

    # Collect single-line and multi-line section headers
    header_matches = list(_HEADER_PATTERN.finditer(text))
    header_matches.extend(list(_MULTI_LINE_HEADER_PATTERN.finditer(text)))
    header_matches.sort(key=lambda m: m.start())

    # 2. Front-matter inspection: detect if the document declares itself as a bibliography
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    front_lines = lines[:FRONT_MATTER_MAX_LINES]
    title_declaration = None
    for line in front_lines:
        if _TITLE_PAGE_PATTERN.search(line) and len(line.split()) <= 25:
            title_declaration = line
            break

    if title_declaration:
        decl_lower = title_declaration.lower()
        is_annotated_title = "annotated" in decl_lower
        # If there is an explicit section heading separating front-matter from entries,
        # slice from the section heading.
        if header_matches:
            best_match = header_matches[-1]
            candidate = text[best_match.end() :].strip()
            heading = best_match.group(0).strip().replace("\n", " ")
            body = text[: best_match.start()].strip()
            kind = (
                DocumentKind.ANNOTATED_BIBLIOGRAPHY
                if (is_annotated_title or _looks_annotated(candidate))
                else DocumentKind.BIBLIOGRAPHY
            )
            return DetectionOutcome(
                bibliography_text=candidate,
                body_text=body,
                method=DetectionMethod.SECTION_HEADER,
                kind=kind,
                confidence=0.95,
                notes=[f'Identified via front-matter title and section heading "{heading}".'],
            )

        # Standalone bibliography catalog with no internal section heading
        kind = (
            DocumentKind.ANNOTATED_BIBLIOGRAPHY
            if (is_annotated_title or _looks_annotated(stripped))
            else DocumentKind.BIBLIOGRAPHY
        )
        return DetectionOutcome(
            bibliography_text=stripped,
            body_text="",
            method=DetectionMethod.TITLE_PAGE,
            kind=kind,
            confidence=0.95,
            notes=[f'The document declares in its front matter: "{title_declaration[:80]}".'],
        )

    # 3. An explicit section heading (for research papers).
    for match in reversed(header_matches):
        candidate = text[match.end() :].strip()
        if candidate:
            heading = match.group(0).strip().replace("\n", " ")
            body = text[: match.start()].strip()
            coverage = len(candidate) / len(stripped)
            kind = (
                DocumentKind.BIBLIOGRAPHY
                if coverage >= REFERENCE_ONLY_COVERAGE
                else DocumentKind.RESEARCH_PAPER
            )
            if kind is DocumentKind.BIBLIOGRAPHY and _looks_annotated(candidate):
                kind = DocumentKind.ANNOTATED_BIBLIOGRAPHY
            return DetectionOutcome(
                bibliography_text=candidate,
                body_text=body,
                method=DetectionMethod.SECTION_HEADER,
                kind=kind,
                confidence=0.9,
                notes=[f'Matched the heading "{heading}".'],
            )

    # 4. Density scan across the tail of the document.
    lines = text.split("\n")
    midpoint = len(lines) // 2
    tail = [line.strip() for line in lines[midpoint:] if line.strip()]

    if _density(tail) > BIBLIOGRAPHY_DENSITY_THRESHOLD:
        start = _find_dense_block_start(lines, midpoint)
        candidate = "\n".join(lines[start:]).strip()
        selected = [line.strip() for line in lines[start:] if line.strip()]
        density = _density(selected)

        if candidate and density > BIBLIOGRAPHY_DENSITY_THRESHOLD:
            body = "\n".join(lines[:start]).strip()
            coverage = len(candidate) / len(stripped)
            kind = (
                DocumentKind.BIBLIOGRAPHY
                if coverage >= REFERENCE_ONLY_COVERAGE
                else DocumentKind.RESEARCH_PAPER
            )
            if _looks_annotated(candidate):
                kind = DocumentKind.ANNOTATED_BIBLIOGRAPHY
            return DetectionOutcome(
                bibliography_text=candidate,
                body_text=body,
                method=DetectionMethod.DENSITY_SCAN,
                kind=kind,
                confidence=min(0.85, density),
                notes=[
                    (
                        "No references heading was present, so the reference block was "
                        f"located by citation density ({density:.0%} of its lines)."
                    ),
                ],
            )

    # 5. Nothing bibliographic here.
    return DetectionOutcome(
        bibliography_text="",
        body_text=stripped,
        method=DetectionMethod.NONE,
        kind=DocumentKind.NON_ACADEMIC,
        confidence=0.0,
        notes=[
            (
                "No references heading and no dense block of citations were found, so "
                "no citations were invented for this document."
            ),
        ],
    )


def detect_bibliography_section(text: str, force_parse: bool = False) -> str:
    """Find and return the bibliography section of the text.

    This is the stable, string-returning facade over
    :func:`characterize_document`.

    Args:
        text: The full text of the document.
        force_parse: If True, treat the entire text as a bibliography.

    Returns:
        The extracted bibliography text, or an empty string if none is found.
    """
    return characterize_document(text, force_parse=force_parse).bibliography_text


__all__ = [
    "DetectionOutcome",
    "characterize_document",
    "detect_bibliography_section",
]
