"""Base extractor contract for PaperMint.

Every concrete extractor converts a byte stream into UTF-8 text and, where the
format exposes it, a real page or slide count. Extractors raise
:class:`~papermint.errors.ExtractionError` subclasses rather than returning an
empty string, so the orchestration layer can distinguish "this file is
corrupt" from "this file contains no words".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """The text and structural metadata recovered from a source file.

    Attributes:
        text: The full extracted text.
        page_count: Number of pages or slides, or 0 when the format has none.
        pages: Per-page text, empty for formats without page structure.
        warnings: Non-fatal notes raised while reading the file.
    """

    text: str
    page_count: int = 0
    pages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = field(default=())

    @property
    def is_empty(self) -> bool:
        """Whether the document yielded no usable text."""
        return not self.text.strip()


class BaseExtractor(ABC):
    """Abstract base class for all file extractors."""

    #: Human-readable name used in diagnostics and the UI.
    name: ClassVar[str] = "document"

    #: MIME types this extractor claims.
    mime_types: ClassVar[frozenset[str]] = frozenset()

    #: Lowercase file extensions, without a leading dot.
    extensions: ClassVar[frozenset[str]] = frozenset()

    @abstractmethod
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from the given file bytes.

        Args:
            file_bytes: The bytes of the file to extract text from.

        Returns:
            The extracted text as a string.

        Raises:
            CorruptedDocumentError: If the bytes cannot be decoded.
        """

    def extract_document(self, file_bytes: bytes) -> ExtractedDocument:
        """Extract text plus structural metadata.

        Subclasses that can report a page count should override this. The
        default implementation delegates to :meth:`extract_text`.

        Args:
            file_bytes: The bytes of the file to extract.

        Returns:
            An :class:`ExtractedDocument` describing the file.
        """
        return ExtractedDocument(text=self.extract_text(file_bytes))

    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type.

        Args:
            mime_type: The MIME type to check.

        Returns:
            True if the extractor supports the MIME type, False otherwise.
        """
        return (mime_type or "").lower() in self.mime_types


__all__ = ["BaseExtractor", "ExtractedDocument"]
