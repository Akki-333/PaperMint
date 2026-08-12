"""Component for rendering a single citation card."""

import streamlit as st
from papermint.models import Citation, CitationStyle

def render_citation_card(citation: Citation, index: int) -> None:
    """Render a single citation as a styled card in Streamlit.
    
    Args:
        citation (Citation): The citation object to render.
        index (int): The 1-based index of the citation in the list.
    """
    # Format author string safely
    authors_str = citation.author_string if citation.author_string else "Unknown Authors"
    
    # Format title safely
    title_str = citation.title if citation.title else "Unknown Title"
    
    # Format year safely
    year_str = f" ({citation.year})" if citation.year else ""
    
    # Format journal info safely
    journal_info = []
    if getattr(citation, 'journal', None):
        journal_info.append(f"*{citation.journal}*")
    if getattr(citation, 'volume', None):
        journal_info.append(f"**{citation.volume}**")
    if getattr(citation, 'issue', None):
        journal_info.append(f"({citation.issue})")
    if getattr(citation, 'pages', None):
        journal_info.append(f"pp. {citation.pages}")
    
    journal_str = ", ".join(journal_info) if journal_info else ""
    
    # Construct the badge HTML if style is known
    badge_html = ""
    if citation.style != CitationStyle.UNKNOWN:
        style_name = citation.style.value if hasattr(citation.style, "value") else str(citation.style)
        badge_html = f'<span class="style-badge">{style_name}</span>'
        
    # Construct DOI link if present
    doi_html = ""
    if citation.doi:
        doi_url = f"https://doi.org/{citation.doi}" if not str(citation.doi).startswith("http") else citation.doi
        doi_html = f'<div style="margin-top: 8px; font-size: 0.9em;">🔗 <a href="{doi_url}" target="_blank" style="color: #60A5FA;">{citation.doi}</a></div>'
        
    # Confidence bar width
    confidence_pct = max(0.0, min(100.0, float(citation.confidence) * 100)) if citation.confidence else 0.0

    html = f"""
    <div class="citation-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div class="citation-title">{index}. {title_str}</div>
            <div>{badge_html}</div>
        </div>
        <div style="color: #CBD5E1; margin-bottom: 4px;">{authors_str}{year_str}</div>
        <div style="color: #94A3B8; font-size: 0.9em;">{journal_str}</div>
        {doi_html}
        <div class="confidence-container" title="Confidence: {confidence_pct:.1f}%">
            <div class="confidence-bar" style="width: {confidence_pct}%;"></div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
