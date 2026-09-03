"""Pydantic data models for PaperMint.

These models are the single source of truth for all data flowing through the
application, from extraction to export. They are pure Pydantic v2 and import
nothing from Streamlit, so they can be used from a CLI, a web service or a
test runner.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from papermint.config import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_REVIEW,
    WORDS_PER_PAGE,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CitationStyle(str, Enum):
    """Supported academic citation styles."""

    APA = "apa"
    MLA = "mla"
    IEEE = "ieee"
    CHICAGO = "chicago"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        """Return the human-facing name of the style."""
        return "Unknown" if self is CitationStyle.UNKNOWN else self.value.upper()


class EntryType(str, Enum):
    """Types of bibliographic entries."""

    ARTICLE = "article"
    BOOK = "book"
    INPROCEEDINGS = "inproceedings"
    INCOLLECTION = "incollection"
    THESIS = "thesis"
    REPORT = "report"
    MISC = "misc"

    @property
    def label(self) -> str:
        """Return the human-facing name of the entry type."""
        return {
            EntryType.ARTICLE: "Journal article",
            EntryType.BOOK: "Book",
            EntryType.INPROCEEDINGS: "Conference paper",
            EntryType.INCOLLECTION: "Book chapter",
            EntryType.THESIS: "Thesis",
            EntryType.REPORT: "Report",
            EntryType.MISC: "Other",
        }[self]


class ConfidenceBand(str, Enum):
    """Qualitative band describing how complete a parsed citation is."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label(self) -> str:
        """Return the human-facing band name."""
        return {
            ConfidenceBand.HIGH: "Complete",
            ConfidenceBand.MEDIUM: "Partial",
            ConfidenceBand.LOW: "Sparse",
        }[self]

    @classmethod
    def from_score(cls, score: float) -> ConfidenceBand:
        """Map a 0.0 to 1.0 confidence score onto a band.

        Args:
            score: The normalised confidence score.

        Returns:
            The matching confidence band.
        """
        if score >= CONFIDENCE_HIGH:
            return cls.HIGH
        if score >= CONFIDENCE_MEDIUM:
            return cls.MEDIUM
        return cls.LOW


class DocumentKind(str, Enum):
    """How the pipeline characterised the uploaded document."""

    RESEARCH_PAPER = "research_paper"
    BIBLIOGRAPHY = "bibliography"
    ANNOTATED_BIBLIOGRAPHY = "annotated_bibliography"
    NON_ACADEMIC = "non_academic"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        """Return the human-facing document kind."""
        return {
            DocumentKind.RESEARCH_PAPER: "Research paper",
            DocumentKind.BIBLIOGRAPHY: "Reference list",
            DocumentKind.ANNOTATED_BIBLIOGRAPHY: "Annotated bibliography",
            DocumentKind.NON_ACADEMIC: "General document",
            DocumentKind.UNKNOWN: "Unclassified",
        }[self]

    @property
    def has_bibliography(self) -> bool:
        """Whether documents of this kind are expected to yield citations."""
        return self in {
            DocumentKind.RESEARCH_PAPER,
            DocumentKind.BIBLIOGRAPHY,
            DocumentKind.ANNOTATED_BIBLIOGRAPHY,
        }


class DetectionMethod(str, Enum):
    """Which strategy located the bibliography inside the document."""

    FORCED = "forced"
    TITLE_PAGE = "title_page"
    SECTION_HEADER = "section_header"
    DENSITY_SCAN = "density_scan"
    NONE = "none"

    @property
    def label(self) -> str:
        """Return the human-facing description of the strategy."""
        return {
            DetectionMethod.FORCED: "Forced by the reader",
            DetectionMethod.TITLE_PAGE: "Title page declares a bibliography",
            DetectionMethod.SECTION_HEADER: "Matched a references heading",
            DetectionMethod.DENSITY_SCAN: "Detected by citation density",
            DetectionMethod.NONE: "No bibliography found",
        }[self]


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class Author(BaseModel):
    """Represents a single author."""

    given: str = ""
    family: str = ""

    @property
    def full_name(self) -> str:
        """Return 'Given Family' format."""
        return f"{self.given} {self.family}".strip()

    @property
    def citation_name(self) -> str:
        """Return 'Family, Given' format (used in citations)."""
        if self.family and self.given:
            return f"{self.family}, {self.given}"
        return self.family or self.given

    @property
    def initials(self) -> str:
        """Return the author's initials, for compact display."""
        parts = [p for p in (self.given, self.family) if p]
        return "".join(p[0].upper() for p in parts if p[0].isalpha())

    def __str__(self) -> str:
        return self.citation_name


class Citation(BaseModel):
    """A single parsed citation or bibliographic reference."""

    title: str = ""
    authors: list[Author] = Field(default_factory=list)
    year: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    publisher: str = ""
    address: str = ""
    edition: str = ""
    booktitle: str = ""
    raw_text: str = ""
    style: CitationStyle = CitationStyle.UNKNOWN
    entry_type: EntryType = EntryType.ARTICLE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_file: str = ""
    edited: bool = False

    # -- Identity -----------------------------------------------------------

    @property
    def cite_key(self) -> str:
        """Generate a BibTeX-style cite key: firstauthor_year_firstword."""
        author_part = ""
        if self.authors:
            author_part = self.authors[0].family.lower().replace(" ", "")
        year_part = self.year
        title_word = ""
        if self.title:
            skip_words = {"a", "an", "the", "on", "in", "of", "for", "and", "to"}
            for word in self.title.split():
                clean = word.strip(",.;:\"'").lower()
                if clean and clean not in skip_words:
                    title_word = clean
                    break
        parts = [p for p in [author_part, year_part, title_word] if p]
        return "_".join(parts) if parts else "unknown"

    # -- Display helpers ----------------------------------------------------

    @property
    def author_string(self) -> str:
        """Return a formatted author string for display."""
        if not self.authors:
            return ""
        names = [a.citation_name for a in self.authors]
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} & {names[1]}"
        return ", ".join(names[:-1]) + f", & {names[-1]}"

    @property
    def short_author_string(self) -> str:
        """Return a compact author string that stays readable on one line."""
        if not self.authors:
            return ""
        first = self.authors[0].citation_name
        if len(self.authors) == 1:
            return first
        if len(self.authors) == 2:
            return f"{first} & {self.authors[1].citation_name}"
        return f"{first} et al."

    @property
    def display_title(self) -> str:
        """Return the title, or a readable stand-in when none was parsed.

        Never returns a placeholder such as "Untitled"; when the parser could
        not isolate a title the opening of the raw entry is shown instead, so
        the reader still sees real content.
        """
        if self.title:
            return self.title
        raw = " ".join(self.raw_text.split())
        if not raw:
            return "Empty entry"
        return raw[:110].rstrip(" ,;:-") + "..." if len(raw) > 110 else raw

    @property
    def is_parsed(self) -> bool:
        """Whether the parser isolated a real title for this entry."""
        return bool(self.title)

    @property
    def venue(self) -> str:
        """Return the publication venue: journal, book title or publisher."""
        return self.journal or self.booktitle or self.publisher

    @property
    def locator(self) -> str:
        """Return the volume, issue and page locator as a single string."""
        parts: list[str] = []
        if self.volume:
            parts.append(f"vol. {self.volume}")
        if self.issue:
            parts.append(f"no. {self.issue}")
        if self.pages:
            parts.append(f"pp. {self.pages}")
        return ", ".join(parts)

    @property
    def doi_url(self) -> str:
        """Return a resolvable URL for the DOI, or the raw URL as a fallback."""
        if self.doi:
            doi = str(self.doi)
            return doi if doi.startswith("http") else f"https://doi.org/{doi}"
        return self.url

    # -- Quality ------------------------------------------------------------

    @property
    def fields_found(self) -> int:
        """Count of non-empty core fields (used for confidence calculation)."""
        core_fields = [
            self.title,
            self.year,
            self.journal,
            self.doi,
            self.volume,
            self.pages,
            self.publisher,
        ]
        count = sum(1 for f in core_fields if f)
        if self.authors:
            count += 1
        return count

    @property
    def confidence_band(self) -> ConfidenceBand:
        """Return the qualitative band for this citation's confidence."""
        return ConfidenceBand.from_score(self.confidence)

    @property
    def needs_review(self) -> bool:
        """Whether a human should verify this citation before exporting."""
        return self.confidence < CONFIDENCE_REVIEW

    @property
    def missing_fields(self) -> list[str]:
        """List the human-readable names of absent core fields."""
        checks = {
            "title": self.title,
            "authors": "x" if self.authors else "",
            "year": self.year,
            "venue": self.venue,
            "DOI": self.doi,
        }
        return [name for name, value in checks.items() if not value]


class DocumentStats(BaseModel):
    """Descriptive statistics about an extracted document."""

    word_count: int = 0
    character_count: int = 0
    line_count: int = 0
    sentence_count: int = 0
    page_count: int = 0

    @property
    def estimated_pages(self) -> int:
        """Return the real page count, or an estimate derived from words."""
        if self.page_count:
            return self.page_count
        return max(1, round(self.word_count / WORDS_PER_PAGE)) if self.word_count else 0

    @property
    def reading_minutes(self) -> int:
        """Return an approximate reading time in whole minutes."""
        return max(1, round(self.word_count / 220)) if self.word_count else 0


class ExtractionResult(BaseModel):
    """Complete result of processing a document."""

    citations: list[Citation] = Field(default_factory=list)
    discarded: list[Citation] = Field(default_factory=list)
    raw_text: str = ""
    bibliography_text: str = ""
    source_filename: str = ""
    detected_style: CitationStyle = CitationStyle.UNKNOWN
    style_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    page_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    document_kind: DocumentKind = DocumentKind.UNKNOWN
    detection_method: DetectionMethod = DetectionMethod.NONE
    stats: DocumentStats = Field(default_factory=DocumentStats)
    duration_ms: int = 0

    @property
    def citation_count(self) -> int:
        """Return the number of parsed citations."""
        return len(self.citations)

    @property
    def discarded_count(self) -> int:
        """Return the number of segments rejected as non-bibliographic."""
        return len(self.discarded)

    @property
    def segment_count(self) -> int:
        """Return how many segments the bibliography block was split into."""
        return len(self.citations) + len(self.discarded)

    @property
    def has_citations(self) -> bool:
        """Whether any citation was parsed from this document."""
        return bool(self.citations)

    @property
    def average_confidence(self) -> float:
        """Return the mean confidence across all parsed citations."""
        if not self.citations:
            return 0.0
        return sum(c.confidence for c in self.citations) / len(self.citations)

    @property
    def review_queue(self) -> list[Citation]:
        """Return the citations a human should verify before export."""
        return [c for c in self.citations if c.needs_review]

    @property
    def is_reference_only(self) -> bool:
        """Whether the document is a bibliography with no narrative body."""
        return self.document_kind in {
            DocumentKind.BIBLIOGRAPHY,
            DocumentKind.ANNOTATED_BIBLIOGRAPHY,
        }


class BatchFileResult(BaseModel):
    """Outcome of processing one file inside a batch run."""

    filename: str
    result: ExtractionResult | None = None
    error: str = ""
    error_kind: str = ""

    @property
    def succeeded(self) -> bool:
        """Whether the file was processed without a fatal error."""
        return self.error == "" and self.result is not None

    @property
    def citation_count(self) -> int:
        """Return the number of citations found in this file."""
        return self.result.citation_count if self.result else 0


class BatchResult(BaseModel):
    """Aggregated outcome of a multi-document batch run."""

    files: list[BatchFileResult] = Field(default_factory=list)
    duration_ms: int = 0

    @property
    def citations(self) -> list[Citation]:
        """Return every citation found across all files, in file order."""
        return [c for f in self.files if f.result for c in f.result.citations]

    @property
    def file_count(self) -> int:
        """Return the number of files in the run."""
        return len(self.files)

    @property
    def success_count(self) -> int:
        """Return how many files were processed without a fatal error."""
        return sum(1 for f in self.files if f.succeeded)

    @property
    def error_count(self) -> int:
        """Return how many files failed."""
        return sum(1 for f in self.files if not f.succeeded)

    @property
    def citation_count(self) -> int:
        """Return the total number of citations across the run."""
        return len(self.citations)

    @property
    def average_confidence(self) -> float:
        """Return the mean confidence across every citation in the run."""
        found = self.citations
        if not found:
            return 0.0
        return sum(c.confidence for c in found) / len(found)


__all__ = [
    "Author",
    "BatchFileResult",
    "BatchResult",
    "Citation",
    "CitationStyle",
    "ConfidenceBand",
    "DetectionMethod",
    "DocumentKind",
    "DocumentStats",
    "EntryType",
    "ExtractionResult",
]
