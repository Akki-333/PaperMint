"""CSV and Excel exporter module for PaperMint."""

import io
import pandas as pd
from typing import Optional

from papermint.models import Citation


def _citations_to_dataframe(citations: list[Citation]) -> pd.DataFrame:
    """Convert a list of citations to a pandas DataFrame.
    
    Args:
        citations: List of Citation objects.
        
    Returns:
        A pandas DataFrame with citation data.
    """
    data = []
    for citation in citations:
        if hasattr(citation, "author_string") and citation.author_string:
            author_string = citation.author_string
        elif citation.authors:
            author_string = "; ".join(author.full_name for author in citation.authors if author.full_name)
        else:
            author_string = ""
            
        data.append({
            "Title": citation.title or "",
            "Authors": author_string,
            "Year": citation.year or "",
            "Journal": citation.journal or "",
            "Volume": citation.volume or "",
            "Issue": citation.issue or "",
            "Pages": citation.pages or "",
            "DOI": citation.doi or "",
            "URL": citation.url or "",
            "Publisher": citation.publisher or "",
            "Confidence": citation.confidence or 0.0
        })
    return pd.DataFrame(data)


def export_csv(citations: list[Citation]) -> str:
    """Export citations as a CSV string.

    Args:
        citations: List of Citation objects to export.

    Returns:
        A CSV formatted string containing the citations.
    """
    df = _citations_to_dataframe(citations)
    return df.to_csv(index=False)


def export_excel(citations: list[Citation]) -> io.BytesIO:
    """Export citations as an Excel (.xlsx) file in memory.

    Args:
        citations: List of Citation objects to export.

    Returns:
        A BytesIO object containing the Excel file data.
    """
    df = _citations_to_dataframe(citations)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Citations')
    output.seek(0)
    return output
