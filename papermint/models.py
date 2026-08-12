"""Pydantic data models for PaperMint.

These models are the single source of truth for all data flowing through the
application — from extraction to export.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

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


class EntryType(str, Enum):
    """Types of bibliographic entries."""

    ARTICLE = "article"
    BOOK = "book"
    INPROCEEDINGS = "inproceedings"
    INCOLLECTION = "incollection"
    THESIS = "thesis"
    REPORT = "report"
    MISC = "misc"


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

    def __str__(self) -> str:
        return self.citation_name


class Citation(BaseModel):
    """A single parsed citation / bibliographic reference."""

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

    @property
    def cite_key(self) -> str:
        """Generate a BibTeX-style cite key: firstauthor_year_firstword."""
        author_part = ""
        if self.authors:
            author_part = self.authors[0].family.lower().replace(" ", "")
        year_part = self.year
        title_word = ""
        if self.title:
            # Take the first significant word from the title
            skip_words = {"a", "an", "the", "on", "in", "of", "for", "and", "to"}
            for word in self.title.split():
                clean = word.strip(",.;:\"'").lower()
                if clean and clean not in skip_words:
                    title_word = clean
                    break
        parts = [p for p in [author_part, year_part, title_word] if p]
        return "_".join(parts) if parts else "unknown"

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
    def fields_found(self) -> int:
        """Count of non-empty core fields (used for confidence calculation)."""
        core_fields = [
            self.title, self.year, self.journal, self.doi,
            self.volume, self.pages, self.publisher,
        ]
        count = sum(1 for f in core_fields if f)
        if self.authors:
            count += 1
        return count


class ExtractionResult(BaseModel):
    """Complete result of processing a document."""

    citations: list[Citation] = Field(default_factory=list)
    raw_text: str = ""
    source_filename: str = ""
    detected_style: CitationStyle = CitationStyle.UNKNOWN
    style_confidence: float = 0.0
    summary: str = ""
    page_count: int = 0
    warnings: list[str] = Field(default_factory=list)

    @property
    def citation_count(self) -> int:
        return len(self.citations)
