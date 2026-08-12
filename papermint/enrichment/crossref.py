"""CrossRef API enrichment module for citation metadata."""

import re
from typing import Optional

from habanero import Crossref

from papermint.models import Citation, Author, EntryType
from papermint.config import CROSSREF_MAILTO


def lookup_doi(doi: str) -> Optional[Citation]:
    """Look up citation metadata from CrossRef by DOI.

    Args:
        doi: The Document Object Identifier (DOI) to look up.

    Returns:
        A Citation object if metadata is found, None otherwise.
    """
    if not doi:
        return None

    try:
        cr = Crossref(mailto=CROSSREF_MAILTO)
        response = cr.works(ids=doi)
        
        if response.get("status") != "ok":
            return None
            
        msg = response.get("message", {})
        
        # Parse title
        title = msg.get("title", [""])[0] if msg.get("title") else ""
        
        # Parse authors
        authors = []
        for author_data in msg.get("author", []):
            given = author_data.get("given", "")
            family = author_data.get("family", "")
            if given or family:
                authors.append(Author(given=given, family=family))
                
        # Parse year
        year = None
        published_print = msg.get("published-print", {}).get("date-parts", [[None]])[0][0]
        published_online = msg.get("published-online", {}).get("date-parts", [[None]])[0][0]
        year = str(published_print or published_online or "")

        # Parse journal
        journal = msg.get("container-title", [""])[0] if msg.get("container-title") else ""
        
        # Other fields
        volume = msg.get("volume", "")
        issue = msg.get("issue", "")
        pages = msg.get("page", "")
        publisher = msg.get("publisher", "")
        url = msg.get("URL", "")
        
        return Citation(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            publisher=publisher,
            url=url,
            confidence=1.0,
            entry_type=EntryType.ARTICLE
        )
    except Exception as e:
        return None


def extract_dois_from_text(text: str) -> list[str]:
    """Extract all DOIs from a given text string.

    Args:
        text: The text to search for DOIs.

    Returns:
        A list of DOIs found in the text.
    """
    if not text:
        return []
        
    pattern = r'10\.\d{4,9}/[^\s,;\]\)]+'
    return re.findall(pattern, text)
