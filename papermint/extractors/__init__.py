"""File format text extractors."""

from papermint.extractors.pdf_extractor import PDFExtractor as PdfExtractor
from papermint.extractors.image_extractor import ImageExtractor
from papermint.extractors.docx_extractor import DocxExtractor
from papermint.extractors.pptx_extractor import PPTXExtractor as PptxExtractor

__all__ = ["PdfExtractor", "ImageExtractor", "DocxExtractor", "PptxExtractor"]
