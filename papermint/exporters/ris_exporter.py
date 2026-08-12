"""RIS exporter module for PaperMint."""

from papermint.models import Citation, EntryType


def export_ris(citations: list[Citation]) -> str:
    """Export a list of citations as an RIS string.

    Args:
        citations: List of Citation objects to export.

    Returns:
        A formatted RIS string containing all citations.
    """
    entries = []
    
    for citation in citations:
        lines = []
        
        # Map entry type
        ty = "GEN"
        if citation.entry_type == EntryType.ARTICLE:
            ty = "JOUR"
        elif citation.entry_type == EntryType.BOOK:
            ty = "BOOK"
        elif citation.entry_type == EntryType.INPROCEEDINGS:
            ty = "CONF"
        elif citation.entry_type == EntryType.THESIS:
            ty = "THES"
            
        lines.append(f"TY  - {ty}")
        
        for author in citation.authors:
            lines.append(f"AU  - {author.family}, {author.given}")
            
        if citation.title:
            lines.append(f"TI  - {citation.title}")
            
        if citation.journal:
            lines.append(f"JO  - {citation.journal}")
        elif getattr(citation, 'booktitle', None):
            lines.append(f"T2  - {citation.booktitle}")
            
        if citation.year:
            lines.append(f"PY  - {citation.year}")
            
        if citation.volume:
            lines.append(f"VL  - {citation.volume}")
            
        if citation.issue:
            lines.append(f"IS  - {citation.issue}")
            
        if citation.pages:
            page_parts = str(citation.pages).split("-")
            lines.append(f"SP  - {page_parts[0].strip()}")
            if len(page_parts) > 1:
                lines.append(f"EP  - {page_parts[1].strip()}")
                
        if citation.doi:
            lines.append(f"DO  - {citation.doi}")
            
        if citation.url:
            lines.append(f"UR  - {citation.url}")
            
        if citation.publisher:
            lines.append(f"PB  - {citation.publisher}")
            
        lines.append("ER  - ")
        
        entries.append("\n".join(lines))
        
    return "\n\n".join(entries)
