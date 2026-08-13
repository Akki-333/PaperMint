"""Component for rendering a single citation card."""

import streamlit as st

from papermint.models import Citation, CitationStyle


def render_citation_card(citation: Citation, index: int) -> None:
    """Render a single citation as a styled card in Streamlit.

    Args:
        citation (Citation): The citation object to render.
        index (int): The 1-based index of the citation in the list.
    """
    # Format fields safely
    if citation.title:
        title_str = citation.title
    else:
        # Show a trimmed preview of the raw text instead of "Untitled"
        raw_preview = citation.raw_text.strip().replace('\n', ' ')[:80]
        title_str = f"{raw_preview}..." if len(citation.raw_text.strip()) > 80 else raw_preview

    authors_str = citation.author_string if citation.author_string else ""
    year_str = f" ({citation.year})" if citation.year else ""

    # Journal metadata line
    meta_parts = []
    if citation.journal:
        meta_parts.append(f"<em>{citation.journal}</em>")
    if citation.volume:
        meta_parts.append(f"vol. {citation.volume}")
    if citation.issue:
        meta_parts.append(f"no. {citation.issue}")
    if citation.pages:
        meta_parts.append(f"pp. {citation.pages}")
    if citation.publisher:
        meta_parts.append(citation.publisher)
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
        doi_html = f'<div class="citation-doi">\ud83d\udd17 <a href="{doi_url}" target="_blank">{citation.doi}</a></div>'

    # Confidence bar
    confidence_pct = max(0.0, min(100.0, float(citation.confidence) * 100)) if citation.confidence else 0.0
    if confidence_pct >= 60:
        fill_class = "conf-fill-high"
    elif confidence_pct >= 30:
        fill_class = "conf-fill-mid"
    else:
        fill_class = "conf-fill-low"

    # Build HTML — NO INDENTATION to prevent Streamlit from rendering as code block
    html = f'<div class="citation-card">'
    html += f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
    html += f'<div class="citation-title">{index}. {title_str}</div>'
    html += f'<div>{badge_html}</div>'
    html += f'</div>'
    if authors_str:
        html += f'<div class="citation-authors">{authors_str}{year_str}</div>'
    elif year_str:
        html += f'<div class="citation-authors">{year_str.strip()}</div>'
    if meta_str:
        html += f'<div class="citation-meta">{meta_str}</div>'
    html += doi_html
    html += f'<div class="conf-wrap">'
    html += f'<span class="conf-label">Confidence</span>'
    html += f'<div class="conf-track">'
    html += f'<div class="conf-fill {fill_class}" style="width:{confidence_pct:.1f}%;"></div>'
    html += f'</div>'
    html += f'<span class="conf-pct">{confidence_pct:.0f}%</span>'
    html += f'</div>'
    html += f'</div>'

    st.markdown(html, unsafe_allow_html=True)
