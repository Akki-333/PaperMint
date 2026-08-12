"""Module for detecting bibliography sections in extracted text."""

import re

from papermint.config import BIBLIOGRAPHY_HEADERS


def _has_bibliographic_density(text: str) -> bool:
    """Check if the text has high bibliographic density.
    
    Args:
        text: The text to analyze.
        
    Returns:
        True if the text appears to be a bibliography based on density, False otherwise.
    """
    if not text.strip():
        return False
        
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return False
        
    # Count bibliographic indicators
    doi_pattern = re.compile(r'10\.\d{4,9}/[^\s]+')
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    author_pattern = re.compile(r'[A-Z][a-z]+,?\s+[A-Z]\.')
    bracket_pattern = re.compile(r'^\[\d+\]')
    
    indicator_count = 0
    for line in lines:
        has_doi = bool(doi_pattern.search(line))
        has_bracket = bool(bracket_pattern.search(line))
        has_year = bool(year_pattern.search(line))
        has_author = bool(author_pattern.search(line))
        
        # A line is highly likely to be a citation if it has a DOI, starts with a bracket [1],
        # or has BOTH a year and an author pattern. Just a year is too common in normal text.
        if has_doi or has_bracket or (has_year and has_author):
            indicator_count += 1
            
    # If more than 20% of lines are definitively citations, consider it dense
    return (indicator_count / len(lines)) > 0.2

def detect_bibliography_section(text: str) -> str:
    r"""Find and return the bibliography section of the text.
    
    Strategy:
    1. Build regex from BIBLIOGRAPHY_HEADERS to find headers like 'References', 'Bibliography', etc.
       Pattern: r'^\s*(?:\d+\.?\s+)?(?:REFERENCES|Bibliography|Works Cited|...)\s*[:\.]?\s*$'
       Use re.IGNORECASE | re.MULTILINE
    2. If found, return everything after the header match
    3. If not found, scan the last 50% of the text for bibliography-like density
       (count DOIs, year patterns, author patterns)
    4. If still not found, return an empty string to indicate no bibliography is present.
    
    Args:
        text: The full text of the document.
        
    Returns:
        The extracted bibliography text, or an empty string if none is found.
    """
    if not text.strip():
        return ""
        
    # 1. Search for bibliography headers
    escaped_headers = [re.escape(header) for header in BIBLIOGRAPHY_HEADERS]
    headers_pattern = "|".join(escaped_headers)
    pattern = rf'^\s*(?:\d+\.?\s+)?(?:{headers_pattern})\s*[:\.]?\s*$'
    
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 2. If found, return everything after the header
    if match:
        return text[match.end():].strip()
        
    # 3. If not found, check the last 50% of the text
    lines = text.split('\n')
    last_half_idx = int(len(lines) * 0.50)
    last_half_text = "\n".join(lines[last_half_idx:])
    
    if _has_bibliographic_density(last_half_text):
        # We could try to find a more precise start, but for now return the last half
        return last_half_text.strip()
        
    # 4. Fallback: return empty string indicating no bibliography
    return ""
