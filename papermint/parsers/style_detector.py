"""Module for detecting citation styles."""

import re

from papermint.models import CitationStyle


def detect_style(citations: list[str]) -> tuple[CitationStyle, float]:
    """Detect citation style from sample citations. Returns (style, confidence).
    
    Args:
        citations: A list of citation strings.
        
    Returns:
        A tuple containing the detected CitationStyle and a confidence score (0.0 to 1.0).
    """
    if not citations:
        return CitationStyle.UNKNOWN, 0.0
        
    scores = {
        CitationStyle.APA: 0.0,
        CitationStyle.MLA: 0.0,
        CitationStyle.IEEE: 0.0,
        CitationStyle.CHICAGO: 0.0
    }
    
    for cit in citations:
        # APA signals
        # Author initials, (YYYY) after author, & ampersand
        if re.search(r'[A-Z][a-z]+,\s+[A-Z]\.', cit):
            scores[CitationStyle.APA] += 0.5
        if re.search(r'\(\d{4}\)', cit):
            scores[CitationStyle.APA] += 1.0
        if '&' in cit:
            scores[CitationStyle.APA] += 0.5
            
        # MLA signals
        # Full first names, vol. X, no. Y, pp. X-Y, title in quotes
        if re.search(r'vol\.\s*\d+', cit, re.IGNORECASE) or re.search(r'no\.\s*\d+', cit, re.IGNORECASE):
            scores[CitationStyle.MLA] += 1.0
        if re.search(r'pp\.\s*\d+', cit, re.IGNORECASE):
            scores[CitationStyle.MLA] += 0.5
        if re.search(r'"[^"]+"', cit) or re.search(r'“[^”]+”', cit):
            scores[CitationStyle.MLA] += 0.5
            
        # IEEE signals
        # [N] bracket prefix, initials-first, doi: prefix
        if re.search(r'^\[\d+\]', cit.strip()):
            scores[CitationStyle.IEEE] += 1.0
        if re.search(r'[A-Z]\.\s+[A-Z][a-z]+', cit):
            scores[CitationStyle.IEEE] += 0.5
        if re.search(r'doi:', cit, re.IGNORECASE):
            scores[CitationStyle.IEEE] += 0.5
            
        # Chicago signals
        # Volume(Issue): Pages format without vol./no./pp. labels
        if re.search(r'\d+\s*\(\d+\):\s*\d+', cit):
            scores[CitationStyle.CHICAGO] += 1.5
            
    # Find the style with the highest score
    best_style = CitationStyle.UNKNOWN
    best_score = 0.0
    
    for style, score in scores.items():
        if score > best_score:
            best_score = score
            best_style = style
            
    # Calculate confidence based on average score per citation
    max_possible_score = len(citations) * 2.0  # approximate max signals per citation
    if max_possible_score == 0:
        return CitationStyle.UNKNOWN, 0.0
        
    confidence = min(1.0, best_score / max_possible_score)
    
    if confidence < 0.2:
        return CitationStyle.UNKNOWN, confidence
        
    return best_style, confidence
