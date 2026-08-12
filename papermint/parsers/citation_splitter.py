"""Module for splitting bibliography blocks into individual citations."""

import re

def _split_by_numbered_prefixes(text: str) -> list[str]:
    """Split citations by numbered prefixes (e.g., [1], 1., (1))."""
    # Pattern for [1], 1., (1) at the beginning of a line
    pattern = r'(?m)^\s*(?:\[\d+\]|\(\d+\)|\d+\.)\s+'
    parts = re.split(pattern, text)
    # Filter out empty strings
    return [p.strip() for p in parts if p.strip()]

def _split_by_blank_lines(text: str) -> list[str]:
    """Split citations by blank lines."""
    parts = re.split(r'\n\s*\n', text)
    return [p.strip() for p in parts if p.strip()]

def _split_by_hanging_indent(text: str) -> list[str]:
    """Split citations by hanging indent pattern."""
    lines = text.split('\n')
    citations = []
    current_citation = []
    
    for line in lines:
        if not line.strip():
            continue
        # Unindented line starts a new citation
        if line == line.lstrip() and current_citation:
            citations.append("\n".join(current_citation))
            current_citation = [line.strip()]
        else:
            current_citation.append(line.strip())
            
    if current_citation:
        citations.append("\n".join(current_citation))
        
    return citations

def _split_by_author_boundary(text: str) -> list[str]:
    """Split citations by identifying lines starting with author names."""
    lines = text.split('\n')
    citations = []
    current_citation = []
    
    # Pattern for "Lastname, F." or "Lastname, Firstname" at start of line
    author_pattern = re.compile(r'^[A-Z][a-z]+,\s+[A-Z]')
    
    for line in lines:
        if not line.strip():
            continue
        if author_pattern.match(line) and current_citation:
            citations.append("\n".join(current_citation))
            current_citation = [line.strip()]
        else:
            current_citation.append(line.strip())
            
    if current_citation:
        citations.append("\n".join(current_citation))
        
    return citations

def split_citations(text: str) -> list[str]:
    """Split bibliography text into individual citations.
    
    Multi-heuristic pipeline (tried in order):
    1. Numbered prefixes: [1], 1., (1) — split on these patterns
    2. Blank line separation: split on \n\n
    3. Hanging indent: unindented first line + indented continuation
    4. Author boundary: lines starting with 'Lastname, F.' patterns
    5. Fallback: treat as single citation
    
    Args:
        text: The bibliography text block.
        
    Returns:
        A list of individual citation strings.
    """
    if not text.strip():
        return []
        
    # Check for numbered prefixes first
    if re.search(r'(?m)^\s*(?:\[\d+\]|\(\d+\)|\d+\.)\s+', text):
        citations = _split_by_numbered_prefixes(text)
        if len(citations) > 1:
            return citations
            
    # Try blank line separation
    if re.search(r'\n\s*\n', text):
        citations = _split_by_blank_lines(text)
        if len(citations) > 1:
            return citations
            
    # Try hanging indent
    lines = text.split('\n')
    indented_lines = sum(1 for line in lines if line.strip() and line != line.lstrip())
    if indented_lines > 0:
        citations = _split_by_hanging_indent(text)
        if len(citations) > 1:
            return citations
            
    # Try author boundary
    author_pattern = re.compile(r'^[A-Z][a-z]+,\s+[A-Z]')
    author_lines = sum(1 for line in lines if line.strip() and author_pattern.match(line.strip()))
    if author_lines > 1:
        citations = _split_by_author_boundary(text)
        if len(citations) > 1:
            return citations
            
    # Fallback
    return [text.strip()]
