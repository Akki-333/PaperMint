"""Component for the export panel."""

from typing import Any

import streamlit as st

# Note: In a real environment, you'd ensure the below exporters are implemented.
from papermint.exporters import (
    bibtex_exporter,
    csv_exporter,
    docx_exporter,
    pdf_exporter,
    ris_exporter,
)
from papermint.models import Citation


def render_export_panel(citations: list[Citation], key_prefix: str = "export") -> None:
    """Render the export panel with format selection and download buttons.
    
    Args:
        citations (list[Citation]): The list of extracted citations.
        key_prefix (str): Prefix to use for widget keys to ensure uniqueness.
    """
    if not citations:
        st.info("No citations available to export.")
        return
        
    st.markdown('<div class="export-section">', unsafe_allow_html=True)
    st.subheader("📥 Export Citations")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        format_options = ["BibTeX", "RIS", "CSV", "Excel", "Word", "PDF"]
        selected_format = st.selectbox(
            "Format",
            options=format_options,
            key=f"{key_prefix}_format"
        )
        
    with col2:
        default_name = "extracted_citations"
        filename_base = st.text_input(
            "Filename",
            value=default_name,
            key=f"{key_prefix}_filename"
        )
        
    # Prepare export data based on selection
    export_data: Any = None
    mime_type = "text/plain"
    ext = ".txt"
    
    try:
        if selected_format == "BibTeX":
            export_data = bibtex_exporter.export_bibtex(citations)
            mime_type = "text/plain"
            ext = ".bib"
        elif selected_format == "RIS":
            export_data = ris_exporter.export_ris(citations)
            mime_type = "application/x-research-info-systems"
            ext = ".ris"
        elif selected_format == "CSV":
            export_data = csv_exporter.export_csv(citations)
            mime_type = "text/csv"
            ext = ".csv"
        elif selected_format == "Excel":
            export_data = csv_exporter.export_excel(citations)
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = ".xlsx"
        elif selected_format == "Word":
            export_data = docx_exporter.export_docx(citations)
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = ".docx"
        elif selected_format == "PDF":
            export_data = pdf_exporter.export_pdf(citations)
            mime_type = "application/pdf"
            ext = ".pdf"
            
        if export_data is not None:
            st.download_button(
                label=f"Download {selected_format}",
                data=export_data,
                file_name=f"{filename_base}{ext}",
                mime=mime_type,
                key=f"{key_prefix}_btn",
                use_container_width=True,
                type="primary"
            )
            
    except Exception as e:
        st.error(f"Error preparing export: {e!s}")
        
    st.markdown('</div>', unsafe_allow_html=True)
