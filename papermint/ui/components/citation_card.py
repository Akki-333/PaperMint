"""Component for rendering a single citation card."""

import textwrap
import streamlit as st

from papermint.models import Citation, CitationStyle


def render_citation_card(citation: Citation, index: int) -> None:
    """Render a single citation as a styled card in Streamlit.

    Args:
        citation (Citation): The citation object to render.
        index (int): The 1-based index of the citation in the list.
    """
    # Format fields safely
    title_str = citation.title if citation.title else "Untitled"
    authors_str = citation.author_string if citation.author_string else "Unknown Authors"
    year_str = f" ({citation.year})" if citation.year else ""

    # Journal metadata line
    meta_parts = []
    if getattr(citation, 'journal', None):
        meta_parts.append(f"<em>{citation.journal}</em>")
    if getattr(citation, 'volume', None):
        meta_parts.append(f"vol. {citation.volume}")
    if getattr(citation, 'issue', None):
        meta_parts.append(f"no. {citation.issue}")
    if getattr(citation, 'pages', None):
        meta_parts.append(f"pp. {citation.pages}")
    meta_str = ", ".join(meta_parts)

    # Style badge
    badge_html = ""
    if citation.style != CitationStyle.UNKNOWN:
        style_name = citation.style.value.upper() if hasattr(citation.style, "value") else str(citation.style)
        badge_html = f'<span class="style-badge">{style_name}</span>'

    # DOI link
    doi_html = ""
    if citation.doi:
        doi_url = f"https://doi.org/{citation.doi}" if not str(citation.doi).startswith("http") else citation.doi
        doi_html = f'<div class="citation-doi">🔗 <a href="{doi_url}" target="_blank">{citation.doi}</a></div>'

    # Confidence bar — using pure CSS classes instead of raw divs
    confidence_pct = max(0.0, min(100.0, float(citation.confidence) * 100)) if citation.confidence else 0.0
    if confidence_pct >= 60:
        fill_class = "conf-fill-high"
    elif confidence_pct >= 30:
        fill_class = "conf-fill-mid"
    else:
        fill_class = "conf-fill-low"

    html = textwrap.dedent(f"""
    <div class="citation-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div class="citation-title">{index}. {title_str}</div>
            <div>{badge_html}</div>
        </div>
        <div class="citation-authors">{authors_str}{year_str}</div>
        <div class="citation-meta">{meta_str}</div>
        {doi_html}
        <div class="conf-wrap">
            <span class="conf-label">Confidence</span>
            <div class="conf-track">
                <div class="conf-fill {fill_class}" style="width: {confidence_pct:.1f}%;"></div>
            </div>
            <span class="conf-pct">{confidence_pct:.0f}%</span>
        </div>
    </div>
    """)

    st.markdown(html, unsafe_allow_html=True)
