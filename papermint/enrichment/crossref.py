"""CrossRef metadata enrichment.

A DOI that is genuinely absent from CrossRef and a CrossRef that is
unreachable are different situations, and the reader needs to be told which
one happened. The first returns ``None``; the second raises
:class:`~papermint.errors.CrossRefNetworkError`.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from habanero import Crossref

from papermint.config import CROSSREF_MAILTO
from papermint.errors import CrossRefNetworkError
from papermint.models import Author, Citation, EntryType
from papermint.parsers.text_normalizer import normalize_field

logger = logging.getLogger(__name__)

#: A DOI anywhere in a block of text.
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s,;\])]+")

#: Prefixes readers paste in front of a DOI.
_DOI_PREFIX = re.compile(r"^\s*(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)

#: CrossRef work types mapped onto PaperMint entry types.
_TYPE_MAP: dict[str, EntryType] = {
    "journal-article": EntryType.ARTICLE,
    "proceedings-article": EntryType.INPROCEEDINGS,
    "book": EntryType.BOOK,
    "book-chapter": EntryType.INCOLLECTION,
    "monograph": EntryType.BOOK,
    "dissertation": EntryType.THESIS,
    "report": EntryType.REPORT,
    "posted-content": EntryType.MISC,
}


def normalize_doi(doi: str) -> str:
    """Strip the prefixes readers paste around a DOI.

    Args:
        doi: The raw input, which may be a full URL.

    Returns:
        The bare DOI, or an empty string when nothing is left.
    """
    return _DOI_PREFIX.sub("", doi or "").strip().rstrip(".,;")


def _first(values: Any) -> str:
    """Return the first entry of a CrossRef list field.

    Args:
        values: The raw field, usually a list of strings.

    Returns:
        The first value as a string, or an empty string.
    """
    if isinstance(values, list) and values:
        return str(values[0])
    return str(values) if isinstance(values, str) else ""


def _publication_year(message: dict[str, Any]) -> str:
    """Extract the publication year from a CrossRef record.

    Args:
        message: The ``message`` object from the API response.

    Returns:
        A four-digit year, or an empty string.
    """
    for field in ("published-print", "published-online", "issued", "created"):
        parts = message.get(field, {}).get("date-parts", [[None]])
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def lookup_doi(doi: str) -> Citation | None:
    """Look up citation metadata from CrossRef by DOI.

    Args:
        doi: The Document Object Identifier, with or without a URL prefix.

    Returns:
        A fully populated :class:`Citation`, or None when CrossRef has no
        record for this DOI.

    Raises:
        CrossRefNetworkError: If CrossRef cannot be reached or refuses the
            request.
    """
    identifier = normalize_doi(doi)
    if not identifier:
        return None

    try:
        response = Crossref(mailto=CROSSREF_MAILTO).works(ids=identifier)
    except Exception as exc:
        text = str(exc)
        if "404" in text or "not found" in text.lower():
            logger.info("CrossRef has no record for %s", identifier)
            return None
        logger.error("CrossRef request failed for %s: %s", identifier, exc)
        raise CrossRefNetworkError(
            f"CrossRef could not be reached: {exc}",
            remedy="Check the network connection and try again in a moment.",
        ) from exc

    if not isinstance(response, dict) or response.get("status") != "ok":
        return None

    message = response.get("message", {})
    if not message:
        return None

    authors = [
        Author(given=entry.get("given", ""), family=entry.get("family", ""))
        for entry in message.get("author", [])
        if entry.get("given") or entry.get("family")
    ]

    return Citation(
        title=normalize_field(_first(message.get("title"))),
        authors=authors,
        year=_publication_year(message),
        journal=normalize_field(_first(message.get("container-title"))),
        volume=str(message.get("volume", "")),
        issue=str(message.get("issue", "")),
        pages=str(message.get("page", "")),
        doi=identifier,
        publisher=normalize_field(str(message.get("publisher", ""))),
        url=str(message.get("URL", "")),
        confidence=1.0,
        entry_type=_TYPE_MAP.get(str(message.get("type", "")), EntryType.ARTICLE),
    )


def extract_dois_from_text(text: str) -> list[str]:
    """Extract every DOI found in a block of text.

    Args:
        text: The text to search.

    Returns:
        The DOIs in the order they appear, de-duplicated.
    """
    if not text:
        return []
    found = [match.rstrip(".,;") for match in _DOI_PATTERN.findall(text)]
    return list(dict.fromkeys(found))


__all__ = ["extract_dois_from_text", "lookup_doi", "normalize_doi"]
