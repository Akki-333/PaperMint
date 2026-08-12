"""Module for parsing individual citation strings into Citation objects."""

import re
import spacy
from papermint.models import Citation, Author, CitationStyle, EntryType
from papermint.config import SPACY_MODEL

# Load spaCy model at module level (lazy singleton)
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL)
        except OSError:
            # Fallback if model not downloaded
            import spacy.cli
            spacy.cli.download(SPACY_MODEL)
            _nlp = spacy.load(SPACY_MODEL)
    return _nlp

def _extract_doi(text: str) -> str:
    """Extract DOI from citation text."""
    match = re.search(r'10\.\d{4,9}/[^\s,]+', text)
    if match:
        return match.group(0).rstrip('.')
    return ""

def _extract_year(text: str) -> str:
    """Extract publication year from citation text."""
    # Look for year in parentheses first
    match = re.search(r'\((19|20)\d{2}\)', text)
    if match:
        return match.group(0).strip('()')
        
    # Fallback to any 4 digit number that looks like a year
    match = re.search(r'\b(19|20)\d{2}\b', text)
    if match:
        return match.group(0)
    return ""

def _extract_authors_apa(text: str) -> list[Author]:
    """Parse APA style authors: Smith, J. A., & Doe, R. B."""
    authors = []
    # Simplified extraction logic
    parts = re.split(r',\s*&?\s*|(?:\s+&?\s+)', text)
    for part in parts:
        if ',' in part:
            last, first = part.split(',', 1)
            authors.append(Author(given=first.strip(), family=last.strip()))
    return authors

def _extract_authors_ieee(text: str) -> list[Author]:
    """Parse IEEE style authors: J. A. Smith and R. B. Doe."""
    authors = []
    # Simplified extraction logic
    parts = re.split(r',\s*|\s+and\s+', text)
    for part in parts:
        words = part.strip().split()
        if len(words) > 1:
            authors.append(Author(given=" ".join(words[:-1]), family=words[-1]))
    return authors

def _extract_authors_nlp(text: str) -> list[Author]:
    """Extract authors using spaCy PERSON entities."""
    authors = []
    nlp = _get_nlp()
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            words = ent.text.split()
            if len(words) > 1:
                authors.append(Author(given=" ".join(words[:-1]), family=words[-1]))
            else:
                authors.append(Author(given="", family=ent.text))
    return authors

def _extract_title(text: str, style: CitationStyle) -> str:
    """Extract title from citation text."""
    if style in (CitationStyle.MLA, CitationStyle.IEEE):
        match = re.search(r'"([^"]+)"', text) or re.search(r'“([^”]+)”', text)
        if match:
            return match.group(1).strip()
            
    if style == CitationStyle.APA:
        # Title is usually after the year
        year_match = re.search(r'\(\d{4}\)\.', text)
        if year_match:
            after_year = text[year_match.end():].strip()
            # Title ends at the next period before italics (which we can't see, so just split on period)
            parts = after_year.split('.')
            if parts:
                return parts[0].strip()
                
    # Fallback heuristic
    return ""

def _detect_entry_type(text: str) -> EntryType:
    """Detect the entry type of the citation."""
    text_lower = text.lower()
    if 'proceedings' in text_lower or 'conference' in text_lower or 'symposium' in text_lower:
        return EntryType.INPROCEEDINGS
    if 'book' in text_lower or 'press' in text_lower:
        return EntryType.BOOK
    # Default to article
    return EntryType.ARTICLE

def parse_citation(text: str, style: CitationStyle = CitationStyle.UNKNOWN) -> Citation:
    """Parse a single citation string into a Citation object.
    
    Args:
        text: The citation string.
        style: The detected or assumed citation style.
        
    Returns:
        A populated Citation object.
    """
    citation = Citation(
        raw_text=text,
        style=style,
        entry_type=_detect_entry_type(text),
        confidence=0.0
    )
    
    # Extract DOI
    doi = _extract_doi(text)
    if doi:
        citation.doi = doi
        
    # Extract Year
    year = _extract_year(text)
    if year:
        citation.year = year
        
    # Extract Title
    title = _extract_title(text, style)
    if title:
        citation.title = title
        
    # Extract Authors
    if style == CitationStyle.APA:
        authors = _extract_authors_apa(text)
    elif style == CitationStyle.IEEE:
        authors = _extract_authors_ieee(text)
    else:
        authors = _extract_authors_nlp(text)
        
    if authors:
        citation.authors = authors
        
    # Basic field count for confidence
    fields_found = 0
    if getattr(citation, 'title', None): fields_found += 1
    if getattr(citation, 'authors', None): fields_found += 1
    if getattr(citation, 'year', None): fields_found += 1
    if getattr(citation, 'doi', None): fields_found += 1
    if getattr(citation, 'journal', None): fields_found += 1
    if getattr(citation, 'volume', None): fields_found += 1
    if getattr(citation, 'pages', None): fields_found += 1
    if getattr(citation, 'publisher', None): fields_found += 1
    
    citation.confidence = fields_found / 8.0
    
    return citation
