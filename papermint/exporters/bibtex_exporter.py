"""BibTeX exporter module for PaperMint."""

from __future__ import annotations

from papermint.models import Citation


def export_bibtex(citations: list[Citation]) -> str:
    """Export a list of citations as a BibTeX string.

    Args:
        citations: List of Citation objects to export.

    Returns:
        A formatted BibTeX string containing all citations.
    """
    entries = []
    for citation in citations:
        entry_type = citation.entry_type.value.lower() if citation.entry_type else "article"
        cite_key = citation.cite_key or "unknown"

        # Format authors: Family, Given and Family, Given
        formatted_authors = []
        for author in citation.authors:
            formatted_authors.append(f"{author.family}, {author.given}")
        author_str = " and ".join(formatted_authors)

        # Format pages
        pages_str = citation.pages.replace("-", "--") if citation.pages else ""

        fields = []
        if author_str:
            fields.append(f"  author  = {{{author_str}}}")
        if citation.title:
            fields.append(f"  title   = {{{citation.title}}}")
        if citation.journal:
            fields.append(f"  journal = {{{citation.journal}}}")
        if citation.year:
            fields.append(f"  year    = {{{citation.year}}}")
        if citation.volume:
            fields.append(f"  volume  = {{{citation.volume}}}")
        if citation.issue:
            fields.append(f"  number  = {{{citation.issue}}}")
        if pages_str:
            fields.append(f"  pages   = {{{pages_str}}}")
        if citation.doi:
            fields.append(f"  doi     = {{{citation.doi}}}")
        if citation.url:
            fields.append(f"  url     = {{{citation.url}}}")
        if citation.publisher:
            fields.append(f"  publisher = {{{citation.publisher}}}")
        if getattr(citation, "address", None):
            fields.append(f"  address = {{{citation.address}}}")
        if getattr(citation, "booktitle", None):
            fields.append(f"  booktitle = {{{citation.booktitle}}}")

        entry = f"@{entry_type}{{{cite_key},\n"
        entry += ",\n".join(fields)
        entry += "\n}"
        entries.append(entry)

    return "\n\n".join(entries)
