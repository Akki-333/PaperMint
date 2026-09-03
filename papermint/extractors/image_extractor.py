"""Image OCR extractor module for PaperMint."""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageEnhance, ImageOps

from papermint.errors import CorruptedDocumentError, OcrUnavailableError
from papermint.extractors.base import BaseExtractor, ExtractedDocument

logger = logging.getLogger(__name__)

TESSERACT_AVAILABLE = False
try:
    import pytesseract

    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract OCR is not installed or not on PATH.")
except ImportError:  # pragma: no cover - depends on the host environment
    logger.warning("pytesseract is not installed; image OCR is unavailable.")


#: Smallest edge length that still gives Tesseract enough pixels to work with.
_MIN_OCR_EDGE = 1000

#: Tesseract page segmentation mode 3: fully automatic layout analysis.
_TESSERACT_CONFIG = "--psm 3"


class ImageExtractor(BaseExtractor):
    """Extractor for image files using Tesseract OCR."""

    name = "Image"
    mime_types = frozenset({"image/png", "image/jpeg", "image/jpg", "image/tiff"})
    extensions = frozenset({"png", "jpg", "jpeg", "tif", "tiff"})

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """Prepare a scanned page for OCR.

        Converts to greyscale, upscales small scans so glyph strokes survive
        binarisation, and lifts contrast so faded print stays legible.

        Args:
            image: The decoded source image.

        Returns:
            The preprocessed image.
        """
        image = ImageOps.exif_transpose(image)
        image = ImageOps.grayscale(image)

        shortest_edge = min(image.size)
        if shortest_edge and shortest_edge < _MIN_OCR_EDGE:
            scale = _MIN_OCR_EDGE / shortest_edge
            new_size = (round(image.width * scale), round(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)

        image = ImageOps.autocontrast(image, cutoff=1)
        return ImageEnhance.Contrast(image).enhance(1.8)

    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from an image file using OCR.

        Args:
            file_bytes: The raw image bytes.

        Returns:
            The recognised text.

        Raises:
            OcrUnavailableError: If the Tesseract binary is not installed.
            CorruptedDocumentError: If the bytes are not a decodable image.
        """
        return self.extract_document(file_bytes).text

    def extract_document(self, file_bytes: bytes) -> ExtractedDocument:
        """Run OCR and report the result as a single-page document.

        Args:
            file_bytes: The raw image bytes.

        Returns:
            An :class:`ExtractedDocument` with a page count of one.

        Raises:
            OcrUnavailableError: If the Tesseract binary is not installed.
            CorruptedDocumentError: If the bytes are not a decodable image.
        """
        if not TESSERACT_AVAILABLE:
            raise OcrUnavailableError(
                "Optical character recognition is unavailable because the Tesseract "
                "engine was not found on this machine.",
                remedy=(
                    "Install Tesseract OCR and make sure it is on PATH, or upload a "
                    "PDF, Word or PowerPoint file instead."
                ),
            )

        try:
            image = Image.open(io.BytesIO(file_bytes))
            image.load()
        except Exception as exc:
            logger.exception("Failed to decode image")
            raise CorruptedDocumentError(
                "This image could not be decoded. The file may be truncated or in an "
                "unsupported format.",
                remedy="Re-export the scan as a PNG or JPEG and try again.",
            ) from exc

        try:
            text = pytesseract.image_to_string(self._preprocess(image), config=_TESSERACT_CONFIG)
        except Exception as exc:
            logger.exception("OCR failed")
            raise CorruptedDocumentError(
                f"Optical character recognition failed on this image: {exc}"
            ) from exc

        warnings: tuple[str, ...] = ()
        if len(text.split()) < 15:
            warnings = (
                (
                    "Optical character recognition returned very little text. A higher "
                    "resolution scan usually gives a much better result."
                ),
            )

        return ExtractedDocument(text=text, page_count=1, pages=(text,), warnings=warnings)

    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type.

        Args:
            mime_type: The MIME type to check.

        Returns:
            True for any ``image/*`` type.
        """
        return (mime_type or "").lower().startswith("image/")
