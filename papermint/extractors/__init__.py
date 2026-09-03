"""File format text extractors."""

from papermint.extractors.base import BaseExtractor, ExtractedDocument
from papermint.extractors.docx_extractor import DocxExtractor
from papermint.extractors.image_extractor import ImageExtractor
from papermint.extractors.pdf_extractor import PDFExtractor as PdfExtractor
from papermint.extractors.pptx_extractor import PPTXExtractor as PptxExtractor
from papermint.extractors.registry import (
    EXTRACTOR_CLASSES,
    resolve_extractor,
    supported_extensions,
    supported_format_names,
)

__all__ = [
    "EXTRACTOR_CLASSES",
    "BaseExtractor",
    "DocxExtractor",
    "ExtractedDocument",
    "ImageExtractor",
    "PdfExtractor",
    "PptxExtractor",
    "resolve_extractor",
    "supported_extensions",
    "supported_format_names",
]
