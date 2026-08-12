"""Word document extractor module for PaperMint."""

import io
import logging

import docx

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class DocxExtractor(BaseExtractor):
    """Extractor for Word (.docx) files using python-docx."""
    
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from a Word document."""
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text_blocks = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_blocks.append(para.text)
                    
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_blocks.append(" | ".join(row_text))
                        
            return "\n".join(text_blocks)
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX: {e}")
            return ""
            
    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type."""
        return mime_type.lower() == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
