"""Extractor resolution for PaperMint.

The presentation layer should never decide which decoder to run. It hands the
registry a MIME type and a filename, and receives a ready extractor or a typed
:class:`~papermint.errors.UnsupportedFileTypeError`.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from papermint.errors import UnsupportedFileTypeError
from papermint.extractors.base import BaseExtractor
from papermint.extractors.docx_extractor import DocxExtractor
from papermint.extractors.image_extractor import ImageExtractor
from papermint.extractors.pdf_extractor import PDFExtractor
from papermint.extractors.pptx_extractor import PPTXExtractor

logger = logging.getLogger(__name__)

#: Every extractor the application knows about, in resolution order.
EXTRACTOR_CLASSES: tuple[type[BaseExtractor], ...] = (
    PDFExtractor,
    ImageExtractor,
    DocxExtractor,
    PPTXExtractor,
)


def supported_extensions() -> list[str]:
    """List every file extension the registry can handle.

    Returns:
        Sorted, lowercase extensions without a leading dot.
    """
    return sorted({ext for cls in EXTRACTOR_CLASSES for ext in cls.extensions})


def supported_format_names() -> list[str]:
    """List the human-readable names of every supported format.

    Returns:
        The extractor display names, in registration order.
    """
    return [cls.name for cls in EXTRACTOR_CLASSES]


def _extension_of(filename: str) -> str:
    """Return the lowercase extension of a filename, without the dot.

    Args:
        filename: A file name or path.

    Returns:
        The extension, or an empty string when there is none.
    """
    if not filename:
        return ""
    return PurePosixPath(filename.replace("\\", "/")).suffix.lstrip(".").lower()


def resolve_extractor(mime_type: str = "", filename: str = "") -> BaseExtractor:
    """Return the extractor able to read the given file.

    The MIME type reported by the browser is tried first because it is the
    more reliable signal; the filename extension is used as a fallback for
    uploads that arrive as ``application/octet-stream``.

    Args:
        mime_type: The MIME type reported by the upload widget.
        filename: The original file name, used as a fallback signal.

    Returns:
        A ready-to-use extractor instance.

    Raises:
        UnsupportedFileTypeError: If no registered extractor claims the file.
    """
    normalized_mime = (mime_type or "").lower().strip()
    extension = _extension_of(filename)

    for cls in EXTRACTOR_CLASSES:
        extractor = cls()
        if normalized_mime and extractor.supports(normalized_mime):
            logger.debug("Resolved %s by MIME type %s", cls.__name__, normalized_mime)
            return extractor

    for cls in EXTRACTOR_CLASSES:
        if extension and extension in cls.extensions:
            logger.debug("Resolved %s by extension .%s", cls.__name__, extension)
            return cls()

    descriptor = filename or normalized_mime or "this file"
    raise UnsupportedFileTypeError(
        f"PaperMint cannot read {descriptor}.",
        remedy=(
            "Supported formats are " + ", ".join(f".{ext}" for ext in supported_extensions()) + "."
        ),
    )


__all__ = [
    "EXTRACTOR_CLASSES",
    "resolve_extractor",
    "supported_extensions",
    "supported_format_names",
]
