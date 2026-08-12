"""Image OCR extractor module for PaperMint."""

import io
import logging

from PIL import Image, ImageEnhance, ImageOps

from .base import BaseExtractor

logger = logging.getLogger(__name__)

TESSERACT_AVAILABLE = False
try:
    import pytesseract
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract OCR is not installed or not in PATH.")
except ImportError:
    logger.warning("pytesseract is not installed.")

class ImageExtractor(BaseExtractor):
    """Extractor for image files using pytesseract."""
    
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from an image file using OCR."""
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available, cannot extract text from image.")
            return ""
            
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            # Preprocessing
            # Convert to grayscale
            image = ImageOps.grayscale(image)
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from image: {e}")
            return ""
            
    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type."""
        return mime_type.lower().startswith("image/")
