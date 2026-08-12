"""DOI lookup page for the Streamlit UI."""

import streamlit as st

from papermint.enrichment.crossref import lookup_doi
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.export_panel import render_export_panel


def render() -> None:
    """Render the DOI lookup page."""
    # Hero header
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">DOI Lookup</div>
        <div class="hero-subtitle">Fetch rich metadata for any scholarly article using its DOI</div>
    </div>
    """, unsafe_allow_html=True)

    # Input section
    col1, col2 = st.columns([4, 1])
    with col1:
        doi_input = st.text_input(
            "Enter DOI",
            placeholder="e.g., 10.1038/s41586-020-2649-2",
            help="The DOI of the paper you want to look up.",
            label_visibility="collapsed"
        )
    with col2:
        lookup_btn = st.button("🔍 Lookup", use_container_width=True, type="primary")

    if lookup_btn and doi_input:
        doi_clean = doi_input.strip()
        if not doi_clean:
            st.warning("Please enter a valid DOI.")
            return

        with st.spinner("Fetching metadata from CrossRef..."):
            try:
                citation = lookup_doi(doi_clean)

                if citation:
                    st.success("✨ Metadata retrieved successfully!")

                    # Render the citation card
                    render_citation_card(citation, index=1)

                    # Show raw metadata in an expander
                    with st.expander("📋 View Raw Metadata (JSON)"):
                        st.json(citation.model_dump() if hasattr(citation, 'model_dump') else citation.dict())

                    # Single item export
                    st.divider()
                    render_export_panel([citation], key_prefix="doi")
                else:
                    st.error("No metadata found for this DOI. Please check if the DOI is correct.")

            except Exception as e:
                st.error(f"An error occurred during DOI lookup: {e!s}")

    elif not doi_input:
        # Show example DOIs when empty
        st.markdown("---")
        st.markdown("#### 💡 Try these example DOIs:")

        example_dois = [
            ("10.1038/s41586-020-2649-2", "Nature — A deep learning approach"),
            ("10.1126/science.aax9044", "Science — Highly accurate protein structure prediction"),
            ("10.1145/3292500.3330919", "ACM — Knowledge Graphs"),
        ]

        for doi, desc in example_dois:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.caption(f"**{desc}**")
                st.code(doi, language=None)
            with col_b:
                st.write("")
