"""PDF extractor module for PaperMint."""

import logging
import pymupdf  # PyMuPDF
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class PDFExtractor(BaseExtractor):
    """Extractor for PDF files using PyMuPDF (fitz)."""
    
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from a PDF file."""
        try:
            doc = pymupdf.open("pdf", file_bytes)
            text_list = []
            for page in doc:
                text_list.append(page.get_text())
            return "\n".join(text_list)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""
            
    def extract_text_by_page(self, file_bytes: bytes) -> list[tuple[int, str]]:
        """Extract text from a PDF file page by page."""
        try:
            doc = pymupdf.open("pdf", file_bytes)
            pages = []
            for i, page in enumerate(doc):
                pages.append((i + 1, page.get_text()))
            return pages
        except Exception as e:
            logger.error(f"Failed to extract text by page from PDF: {e}")
            return []
            
    def extract_metadata(self, file_bytes: bytes) -> dict[str, str]:
        """Extract metadata from a PDF file."""
        try:
            doc = pymupdf.open("pdf", file_bytes)
            metadata = doc.metadata
            if metadata is None:
                return {}
            # Ensure all values are strings
            return {k: str(v) for k, v in metadata.items() if v is not None}
        except Exception as e:
            logger.error(f"Failed to extract metadata from PDF: {e}")
            return {}
            
    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type."""
        return mime_type.lower() == "application/pdf"
