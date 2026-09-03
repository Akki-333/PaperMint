"""Domain exception hierarchy for PaperMint.

Every failure that originates inside the domain layer is expressed as a
subclass of :class:`PaperMintError`. This lets the presentation layer render
precise, human-readable feedback without inspecting exception messages or
catching bare :class:`Exception`.

The hierarchy intentionally mirrors the pipeline stages:

    PaperMintError
    |-- ExtractionError        (stage 1: document -> text)
    |   |-- UnsupportedFileTypeError
    |   |-- CorruptedDocumentError
    |   |-- EmptyDocumentError
    |   +-- OcrUnavailableError
    |-- ParsingError           (stages 2-4: text -> citations)
    |   +-- StyleDetectionError
    |-- SummarizationError     (stage 5: text -> summary)
    |-- EnrichmentError        (CrossRef / external metadata)
    |   |-- CrossRefNetworkError
    |   +-- DoiNotFoundError
    +-- ExportError            (stage 6: citations -> file)
"""

from __future__ import annotations


class PaperMintError(Exception):
    """Base class for every recoverable PaperMint domain failure.

    Attributes:
        message: The technical description of what went wrong.
        remedy: An optional, user-facing suggestion for how to proceed.
    """

    #: Short, stable label used by the UI to group errors.
    kind: str = "error"

    def __init__(self, message: str, *, remedy: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.remedy = remedy

    def __str__(self) -> str:
        return self.message


# ---------------------------------------------------------------------------
# Stage 1 — Document ingestion and text extraction
# ---------------------------------------------------------------------------


class ExtractionError(PaperMintError):
    """Raised when a document cannot be decoded into text."""

    kind = "extraction"


class UnsupportedFileTypeError(ExtractionError):
    """Raised when no extractor is registered for the supplied file."""

    kind = "unsupported_file"


class CorruptedDocumentError(ExtractionError):
    """Raised when a file is recognised but its bytes cannot be parsed."""

    kind = "corrupted_document"


class EmptyDocumentError(ExtractionError):
    """Raised when a document decodes successfully but yields no usable text."""

    kind = "empty_document"


class OcrUnavailableError(ExtractionError):
    """Raised when an image needs OCR but the Tesseract binary is missing."""

    kind = "ocr_unavailable"


# ---------------------------------------------------------------------------
# Stages 2-4 — Bibliography detection, segmentation and field parsing
# ---------------------------------------------------------------------------


class ParsingError(PaperMintError):
    """Raised when bibliography segmentation or field parsing fails."""

    kind = "parsing"


class StyleDetectionError(ParsingError):
    """Raised when citation style detection fails irrecoverably."""

    kind = "style_detection"


# ---------------------------------------------------------------------------
# Stage 5 — Summarization
# ---------------------------------------------------------------------------


class SummarizationError(PaperMintError):
    """Raised when the summarizer cannot produce any output at all."""

    kind = "summarization"


# ---------------------------------------------------------------------------
# Metadata enrichment
# ---------------------------------------------------------------------------


class EnrichmentError(PaperMintError):
    """Raised when external metadata enrichment fails."""

    kind = "enrichment"


class CrossRefNetworkError(EnrichmentError):
    """Raised when the CrossRef API is unreachable or rate limited."""

    kind = "crossref_network"


class DoiNotFoundError(EnrichmentError):
    """Raised when a DOI is well-formed but not present in CrossRef."""

    kind = "doi_not_found"


# ---------------------------------------------------------------------------
# Stage 6 — Export
# ---------------------------------------------------------------------------


class ExportError(PaperMintError):
    """Raised when citations cannot be serialised to the requested format."""

    kind = "export"


__all__ = [
    "CorruptedDocumentError",
    "CrossRefNetworkError",
    "DoiNotFoundError",
    "EmptyDocumentError",
    "EnrichmentError",
    "ExportError",
    "ExtractionError",
    "OcrUnavailableError",
    "PaperMintError",
    "ParsingError",
    "StyleDetectionError",
    "SummarizationError",
    "UnsupportedFileTypeError",
]
