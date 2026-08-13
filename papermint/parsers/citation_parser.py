"""Module for parsing individual citation strings into Citation objects."""

import re
import logging

from papermint.models import Author, Citation, CitationStyle, EntryType

logger = logging.getLogger(__name__)


def _extract_doi(text: str) -> str:
    """Extract DOI from citation text."""
    match = re.search(r'10\.\d{4,9}/[^\s,;\]\)]+', text)
    if match:
        return match.group(0).rstrip('.').rstrip(',')
    return ""


def _extract_year(text: str) -> str:
    """Extract publication year from citation text."""
    # Look for year in parentheses first (most common)
    match = re.search(r'\((19|20)\d{2}[a-z]?\)', text)
    if match:
        return re.search(r'((?:19|20)\d{2})', match.group(0)).group(1)

    # Then look for standalone year
    match = re.search(r'\b(19|20)\d{2}\b', text)
    if match:
        return match.group(0)
    return ""


def _extract_authors_apa(text: str) -> list[Author]:
    """Parse APA style authors: Smith, J. A., & Doe, R. B. (YYYY)."""
    authors = []
    # Get everything before the year parenthesis
    year_match = re.search(r'\s*\((?:19|20)\d{2}', text)
    author_str = text[:year_match.start()] if year_match else text.split('.')[0]

    # Clean up
    author_str = re.sub(r'^\s*\[?\d+\]?\.?\s*', '', author_str)  # Remove numbering
    author_str = author_str.strip().rstrip('.')

    # Split on ' & ' or ', &' or ' and '
    parts = re.split(r'\s*&\s*|\s+and\s+', author_str)
    for part in parts:
        part = part.strip().rstrip(',')
        if not part:
            continue
        # Match "Lastname, F. M." or "Lastname, Firstname"
        m = re.match(r'([A-Z][a-zA-Z\-\']+),\s+(.+)', part)
        if m:
            authors.append(Author(family=m.group(1).strip(), given=m.group(2).strip().rstrip(',')))
        elif re.match(r'[A-Z]', part):
            words = part.split()
            if len(words) >= 2:
                authors.append(Author(given=' '.join(words[:-1]), family=words[-1]))
            elif len(words) == 1:
                authors.append(Author(family=words[0]))
    return authors


def _extract_authors_ieee(text: str) -> list[Author]:
    """Parse IEEE style authors: J. A. Smith and R. B. Doe, \"Title\"."""
    authors = []
    # Get text before the title (first quote or comma-separated title marker)
    quote_idx = -1
    for q in ['"', '\u201c', ',']:
        idx = text.find(q)
        if idx != -1 and (quote_idx == -1 or idx < quote_idx):
            quote_idx = idx

    author_str = text[:quote_idx] if quote_idx > 0 else text.split(',')[0]
    author_str = re.sub(r'^\s*\[\d+\]\s*', '', author_str).strip().rstrip(',')

    parts = re.split(r'\s+and\s+|,\s+', author_str)
    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue
        words = part.split()
        if len(words) > 1:
            authors.append(Author(given=" ".join(words[:-1]), family=words[-1]))
        elif len(words) == 1 and re.match(r'[A-Z]', words[0]):
            authors.append(Author(family=words[0]))
    return authors


def _extract_authors_generic(text: str) -> list[Author]:
    """Extract authors using regex patterns instead of spaCy NER.

    Uses common academic author patterns rather than general-purpose NER
    which misidentifies content words as person names.
    """
    authors = []

    # Try to isolate the author portion (usually before the year or title)
    year_match = re.search(r'\(?(?:19|20)\d{2}\)?', text)
    if year_match:
        author_str = text[:year_match.start()]
    else:
        # Take text before first period-separated segment
        author_str = text.split('.')[0]

    # Clean up numbering and leading artifacts
    author_str = re.sub(r'^\s*\[?\d+\]?\.?\s*', '', author_str).strip()
    author_str = author_str.rstrip('.').rstrip(',')

    if not author_str:
        return authors

    # Pattern 1: "Lastname, F. M." (APA-like)
    apa_matches = list(re.finditer(r'([A-Z][a-zA-Z\-\']+),\s+([A-Z][.\s]+)', author_str))
    if apa_matches:
        for m in apa_matches:
            authors.append(Author(family=m.group(1).strip(), given=m.group(2).strip().rstrip(',').rstrip('&').strip()))
        return authors

    # Pattern 2: "Lastname, Firstname" (full names with comma)
    name_matches = list(re.finditer(r'([A-Z][a-z]+),\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', author_str))
    if name_matches:
        for m in name_matches:
            authors.append(Author(family=m.group(1).strip(), given=m.group(2).strip()))
        return authors

    # Pattern 3: Split by ' and ' or ' & '
    parts = re.split(r'\s*[&]\s*|\s+and\s+', author_str)
    for part in parts:
        part = part.strip().rstrip(',')
        if not part or len(part) < 3:
            continue
        words = part.split()
        # Only treat as author if it looks like a name (2-4 words, starts with capital)
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w not in (',', '&')):
            if len(words) >= 2:
                authors.append(Author(given=' '.join(words[:-1]), family=words[-1]))
            else:
                authors.append(Author(family=words[0]))

    return authors


def _extract_title(text: str, style: CitationStyle) -> str:
    """Extract title from citation text using multiple strategies."""
    # Strategy 1: Quoted title (IEEE, MLA)
    for pattern in [r'"([^"]{5,})"', r'\u201c([^\u201d]{5,})\u201d']:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().rstrip(',')

    # Strategy 2: APA — title is after "(YYYY). "
    year_match = re.search(r'\(\d{4}[a-z]?\)\.\s*', text)
    if year_match:
        after_year = text[year_match.end():].strip()
        # Title goes until the next period followed by a space and an italic-like word
        # or just the first sentence
        period_match = re.search(r'\.[\s]', after_year)
        if period_match:
            candidate = after_year[:period_match.start()].strip()
            if len(candidate) > 5:
                return candidate

    # Strategy 3: ALL CAPS title (older bibliographies)
    caps_match = re.search(r'(?:^|\s)([A-Z][A-Z\s\-\',:]{8,}[A-Z])(?:\s|$|\.)', text)
    if caps_match:
        title = caps_match.group(1).strip()
        # Exclude publisher-like strings (e.g. "MACMILLAN CO")
        if not re.match(r'^[A-Z]+\s+(CO|INC|LTD|PRESS|PUBLISHING)$', title):
            return title

    # Strategy 4: After year without parentheses — "Author. YYYY. Title. Publisher."
    year_plain = re.search(r'\.\s*((?:19|20)\d{2})\.\s*', text)
    if year_plain:
        after = text[year_plain.end():].strip()
        period_match = re.search(r'\.', after)
        if period_match:
            candidate = after[:period_match.start()].strip()
            if len(candidate) > 5:
                return candidate

    # Strategy 5: Take the longest sentence-like segment (fallback)
    # Split by periods and find the longest segment that isn't the author block
    segments = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    if len(segments) >= 2:
        # Skip the first segment (likely authors) and return the longest remaining
        remaining = segments[1:]
        best = max(remaining, key=len)
        if len(best) > 10:
            return best

    return ""


def _extract_journal(text: str) -> str:
    """Extract journal or publication name from citation text."""
    # Pattern: "Journal Name, vol." or "Journal Name, 12(3)"
    match = re.search(r'[,.]\s*([A-Z][a-zA-Z\s&]+?)\s*,\s*(?:vol\.|\d+\s*\()', text, re.IGNORECASE)
    if match:
        journal = match.group(1).strip()
        if len(journal) > 3:
            return journal

    # Pattern: italic-like marker (text between two periods after title)
    # e.g., "Title. Journal of Something, 12(3), 45-67."
    parts = text.split('.')
    for i, part in enumerate(parts):
        part = part.strip()
        if i >= 2 and re.search(r'\d+\s*\(\d+\)', part):
            # The journal is likely the text before the volume
            j_match = re.match(r'([A-Za-z][A-Za-z\s&]+?)\s*,?\s*\d+', part)
            if j_match:
                return j_match.group(1).strip()
    return ""


def _extract_volume_issue_pages(text: str) -> tuple[str, str, str]:
    """Extract volume, issue, and pages from citation text."""
    volume, issue, pages = "", "", ""

    # Pattern: "vol. 12, no. 3, pp. 45-67"
    vol_match = re.search(r'vol\.?\s*(\d+)', text, re.IGNORECASE)
    if vol_match:
        volume = vol_match.group(1)
    no_match = re.search(r'no\.?\s*(\d+)', text, re.IGNORECASE)
    if no_match:
        issue = no_match.group(1)
    pp_match = re.search(r'pp?\.?\s*([\d]+\s*[-–]\s*[\d]+)', text, re.IGNORECASE)
    if pp_match:
        pages = pp_match.group(1).replace(' ', '')

    # Pattern: "12(3), 45-67" or "12(3): 45-67"
    if not volume:
        combo_match = re.search(r'(\d+)\s*\((\d+)\)\s*[,:.]?\s*(\d+\s*[-–]\s*\d+)?', text)
        if combo_match:
            volume = combo_match.group(1)
            issue = combo_match.group(2)
            if combo_match.group(3):
                pages = combo_match.group(3).replace(' ', '')

    # Standalone pages pattern
    if not pages:
        pages_match = re.search(r'(\d{1,5})\s*[-–]\s*(\d{1,5})', text)
        if pages_match:
            p1, p2 = int(pages_match.group(1)), int(pages_match.group(2))
            if p2 > p1 and (p2 - p1) < 5000:  # Sanity check
                pages = f"{p1}-{p2}"

    return volume, issue, pages


def _extract_publisher(text: str) -> str:
    """Extract publisher from citation text."""
    # Common publisher patterns
    pub_patterns = [
        r'(?:Published by|Publisher:?)\s*([A-Z][a-zA-Z\s&]+)',
        r'([A-Z][a-zA-Z\s]*(?:Press|Publishing|Publishers|Publications|Books|Verlag|University Press))',
        r'([A-Z][a-zA-Z\s]*(?:Co\.|Inc\.|Ltd\.))',
    ]
    for pattern in pub_patterns:
        match = re.search(pattern, text)
        if match:
            pub = match.group(1).strip().rstrip('.')
            if len(pub) > 2:
                return pub
    return ""


def _detect_entry_type(text: str) -> EntryType:
    """Detect the entry type of the citation."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ('proceedings', 'conference', 'symposium', 'workshop')):
        return EntryType.INPROCEEDINGS
    if any(kw in text_lower for kw in ('thesis', 'dissertation')):
        return EntryType.THESIS
    if any(kw in text_lower for kw in ('technical report', 'tech. rep.', 'report no.')):
        return EntryType.REPORT
    if any(kw in text_lower for kw in ('press', 'publisher', 'edition', 'chapter')):
        return EntryType.BOOK
    if re.search(r'vol\.?\s*\d|\d+\s*\(\d+\)|pp?\.\s*\d', text_lower):
        return EntryType.ARTICLE
    return EntryType.MISC


def parse_citation(text: str, style: CitationStyle = CitationStyle.UNKNOWN) -> Citation:
    """Parse a single citation string into a Citation object.

    Args:
        text: The citation string.
        style: The detected or assumed citation style.

    Returns:
        A populated Citation object.
    """
    if not text or not text.strip():
        return Citation(raw_text=text, confidence=0.0)

    citation = Citation(
        raw_text=text,
        style=style,
        entry_type=_detect_entry_type(text),
        confidence=0.0
    )

    # Extract DOI from full text (DOI can be anywhere)
    doi = _extract_doi(text)
    if doi:
        citation.doi = doi

    # ISOLATE CITATION HEADER FROM ANNOTATION PROSE
    # In annotated bibliographies, the citation is usually the first 1-3 lines,
    # followed by a blank line or a long prose paragraph.
    # We split by blank lines and take the first block.
    parts = re.split(r'\n\s*\n', text.strip())
    cit_header = parts[0] if parts else text

    # Extract Year from header
    year = _extract_year(cit_header)
    if year:
        citation.year = year

    # Extract Title from header
    title = _extract_title(cit_header, style)
    if title:
        citation.title = title

    # Extract Authors from header
    if style == CitationStyle.APA:
        authors = _extract_authors_apa(cit_header)
    elif style == CitationStyle.IEEE:
        authors = _extract_authors_ieee(cit_header)
    else:
        authors = _extract_authors_generic(cit_header)

    if authors:
        citation.authors = authors

    # Extract journal metadata from header
    journal = _extract_journal(cit_header)
    if journal:
        citation.journal = journal

    volume, issue, pages = _extract_volume_issue_pages(cit_header)
    if volume:
        citation.volume = volume
    if issue:
        citation.issue = issue
    if pages:
        citation.pages = pages

    # Extract publisher from header
    publisher = _extract_publisher(cit_header)
    if publisher:
        citation.publisher = publisher

    # Compute confidence based on CORE fields only (the ones we actually extract)
    core_fields = 5  # title, authors, year, doi, (journal OR publisher)
    fields_found = 0
    if citation.title:
        fields_found += 1
    if citation.authors:
        fields_found += 1
    if citation.year:
        fields_found += 1
    if citation.doi:
        fields_found += 1
    if citation.journal or citation.publisher:
        fields_found += 1

    # Bonus for extra metadata
    bonus = 0
    if citation.volume:
        bonus += 0.5
    if citation.pages:
        bonus += 0.5

    citation.confidence = min(1.0, (fields_found + bonus) / core_fields)

    return citation
