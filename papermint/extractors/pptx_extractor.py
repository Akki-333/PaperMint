"""PowerPoint extractor module for PaperMint."""

import io
import logging

from pptx import Presentation

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class PPTXExtractor(BaseExtractor):
    """Extractor for PowerPoint (.pptx) files using python-pptx."""
    
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from a PowerPoint presentation."""
        try:
            prs = Presentation(io.BytesIO(file_bytes))
            text_blocks = []
            
            for slide in prs.slides:
                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text_frame") and shape.text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            if paragraph.text.strip():
                                text_blocks.append(paragraph.text)
                                
                # Extract text from notes if present
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = slide.notes_slide.notes_text_frame.text
                    if notes_text.strip():
                        text_blocks.append(notes_text)
                        
            return "\n".join(text_blocks)
        except Exception as e:
            logger.error(f"Failed to extract text from PPTX: {e}")
            return ""
            
    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type."""
        return mime_type.lower() == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
