"""DOI lookup page for the Streamlit UI."""

import streamlit as st

from papermint.enrichment.crossref import lookup_doi
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.export_panel import render_export_panel


def render() -> None:
    """Render the DOI lookup page."""
    st.title("🔍 DOI Lookup")
    st.markdown("Fetch rich metadata for any scholarly article using its DOI (Digital Object Identifier).")
    
    # Input section
    col1, col2 = st.columns([3, 1])
    with col1:
        doi_input = st.text_input(
            "Enter DOI", 
            placeholder="e.g., 10.1038/s41586-020-2649-2",
            help="The DOI of the paper you want to look up."
        )
    with col2:
        st.write("") # Spacer
        st.write("") # Spacer
        lookup_btn = st.button("Lookup", use_container_width=True, type="primary")
        
    if lookup_btn and doi_input:
        doi_clean = doi_input.strip()
        if not doi_clean:
            st.warning("Please enter a valid DOI.")
            return
            
        with st.spinner("Fetching metadata from CrossRef..."):
            try:
                citation = lookup_doi(doi_clean)
                
                if citation:
                    st.success("Metadata retrieved successfully!")
                    
                    st.markdown("### Result")
                    # Render the citation card
                    render_citation_card(citation, index=1)
                    
                    # Show raw metadata in an expander
                    with st.expander("View Raw Metadata (JSON)"):
                        # Convert model to dict for display safely
                        st.json(citation.model_dump() if hasattr(citation, 'model_dump') else citation.dict())
                        
                    # Single item export
                    st.markdown("### Export")
                    render_export_panel([citation], key_prefix="doi")
                else:
                    st.error("No metadata found for this DOI. Please check if the DOI is correct.")
                    
            except Exception as e:
                st.error(f"An error occurred during DOI lookup: {e!s}")
