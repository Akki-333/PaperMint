"""Module for splitting bibliography blocks into individual citations."""

import re


def _looks_like_citation(text: str) -> bool:
    """Check if a text block looks like it could be a citation.
    
    Returns True if the text contains at least one bibliographic indicator.
    """
    text = text.strip()
    if not text or len(text) < 10:
        return False
    indicators = [
        re.search(r'\b(19|20)\d{2}\b', text),             # Year
        re.search(r'10\.\d{4,9}/[^\s]+', text),            # DOI
        re.search(r'[A-Z][a-z]+,\s+[A-Z]', text),         # Author pattern
        re.search(r'^\s*\[\d+\]', text),                   # [1] prefix
        re.search(r'vol\.\s*\d+|pp?\.\s*\d+', text, re.I), # Volume/pages
    ]
    return sum(1 for i in indicators if i) >= 1


def _split_by_numbered_prefixes(text: str) -> list[str]:
    """Split citations by numbered prefixes (e.g., [1], 1., (1))."""
    pattern = r'(?m)(^\s*(?:\[\d+\]|\(\d+\)|\d+\.)\s+)'
    parts = re.split(pattern, text)

    citations = []
    for i in range(1, len(parts), 2):
        prefix = parts[i]
        cit_text = parts[i+1] if i+1 < len(parts) else ""
        citations.append((prefix + cit_text).strip())

    return [c for c in citations if c]


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

    author_pattern = re.compile(r'^[A-Z][a-z]+,\s+[A-Z]')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if author_pattern.match(line_stripped) and current_citation:
            citations.append("\n".join(current_citation))
            current_citation = [line_stripped]
        else:
            current_citation.append(line_stripped)

    if current_citation:
        citations.append("\n".join(current_citation))

    return citations


def split_citations(text: str) -> list[str]:
    """Split bibliography text into individual citations.

    Multi-heuristic pipeline (tried in order):
    1. Numbered prefixes: [1], 1., (1)
    2. Blank line separation: \\n\\n
    3. Hanging indent
    4. Author boundary: lines starting with 'Lastname, F.' patterns
    5. Fallback: treat as single citation

    After splitting, validate that most segments look like citations.

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

    # Try blank line separation — but validate that results look like citations
    if re.search(r'\n\s*\n', text):
        citations = _split_by_blank_lines(text)
        if len(citations) > 1:
            # Validate: at least 40% of segments should look like citations
            citation_count = sum(1 for c in citations if _looks_like_citation(c))
            ratio = citation_count / len(citations)
            if ratio >= 0.4:
                return citations

    # Try hanging indent
    lines = text.split('\n')
    indented_lines = sum(1 for line in lines if line.strip() and line != line.lstrip())
    if indented_lines > 0:
        citations = _split_by_hanging_indent(text)
        if len(citations) > 1:
            citation_count = sum(1 for c in citations if _looks_like_citation(c))
            ratio = citation_count / len(citations)
            if ratio >= 0.4:
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
