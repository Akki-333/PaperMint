"""Base extractor module for PaperMint."""

from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Abstract base class for all file extractors."""
    
    @abstractmethod
    def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from the given file bytes.
        
        Args:
            file_bytes: The bytes of the file to extract text from.
            
        Returns:
            The extracted text as a string.
        """
        pass
        
    @abstractmethod
    def supports(self, mime_type: str) -> bool:
        """Check if this extractor supports the given MIME type.
        
        Args:
            mime_type: The MIME type to check.
            
        Returns:
            True if the extractor supports the MIME type, False otherwise.
        """
        pass
