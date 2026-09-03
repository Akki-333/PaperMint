"""PDF extractor module for PaperMint."""

from __future__ import annotations

import logging

import pymupdf  # PyMuPDF

from papermint.errors import CorruptedDocumentError
from papermint.extractors.base import BaseExtractor, ExtractedDocument

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extractor for PDF files using PyMuPDF."""

    name = "PDF"
    mime_types = frozenset({"application/pdf"})
    extensions = frozenset({"pdf"})

    def _open(self, file_bytes: bytes) -> pymupdf.Document:
        """Open a PDF byte stream.

        Args:
            file_bytes: The raw PDF bytes.

        Returns:
            An open PyMuPDF document.

        Raises:
            CorruptedDocumentError: If the stream is not a readable PDF.
        """
        try:
            return pymupdf.open("pdf", file_bytes)
        except Exception as exc:
            logger.exception("Failed to open PDF stream")
            raise CorruptedDocumentError(
                "This PDF could not be opened. It may be corrupted or password protected.",
                remedy="Try re-saving or re-exporting the PDF, then upload it again.",
            ) from exc

    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from a PDF file.

        Args:
            file_bytes: The raw PDF bytes.

        Returns:
            The concatenated text of every page.

        Raises:
            CorruptedDocumentError: If the stream is not a readable PDF.
        """
        return self.extract_document(file_bytes).text

    def extract_document(self, file_bytes: bytes) -> ExtractedDocument:
        """Extract text along with the real page count.

        Args:
            file_bytes: The raw PDF bytes.

        Returns:
            An :class:`ExtractedDocument` including per-page text.

        Raises:
            CorruptedDocumentError: If the stream is not a readable PDF.
        """
        doc = self._open(file_bytes)
        try:
            pages = tuple(page.get_text() for page in doc)
        except Exception as exc:
            logger.exception("Failed to read PDF pages")
            raise CorruptedDocumentError(
                f"This PDF could not be read to the end: {exc}",
            ) from exc
        finally:
            doc.close()

        warnings: tuple[str, ...] = ()
        if pages and not any(p.strip() for p in pages):
            warnings = (
                (
                    "The PDF contains no embedded text layer. It is most likely a scan; "
                    "upload the pages as images to run OCR instead."
                ),
            )

        return ExtractedDocument(
            text="\n".join(pages),
            page_count=len(pages),
            pages=pages,
            warnings=warnings,
        )

    def extract_text_by_page(self, file_bytes: bytes) -> list[tuple[int, str]]:
        """Extract text from a PDF file page by page.

        Args:
            file_bytes: The raw PDF bytes.

        Returns:
            A list of ``(page_number, text)`` pairs, numbered from 1.
        """
        document = self.extract_document(file_bytes)
        return list(enumerate(document.pages, start=1))

    def extract_metadata(self, file_bytes: bytes) -> dict[str, str]:
        """Extract document metadata from a PDF file.

        Args:
            file_bytes: The raw PDF bytes.

        Returns:
            The PDF metadata dictionary with all values coerced to strings.
        """
        doc = self._open(file_bytes)
        try:
            metadata = doc.metadata or {}
            return {k: str(v) for k, v in metadata.items() if v is not None}
        finally:
            doc.close()
