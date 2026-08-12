"""Batch processing page for the Streamlit UI."""

import streamlit as st

from papermint.extractors import PdfExtractor, ImageExtractor, DocxExtractor, PptxExtractor
from papermint.parsers.bibliography_detector import detect_bibliography_section
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.parsers.citation_parser import parse_citation
from papermint.config import IMAGE_MIME_TYPES, PDF_MIME_TYPE

from papermint.ui.components.file_uploader import render_file_uploader
from papermint.ui.components.export_panel import render_export_panel

def render() -> None:
    """Render the batch processing page."""
    st.title("📁 Batch Processing")
    st.markdown("Upload multiple documents to extract citations in bulk.")
    
    uploaded_files = render_file_uploader(key="batch_upload", accept_multiple=True)
    
    if uploaded_files:
        st.write(f"Processing {len(uploaded_files)} files...")
        
        progress_bar = st.progress(0)
        all_citations = []
        
        for i, file in enumerate(uploaded_files):
            # Process each file
            try:
                # Basic extractor logic
                file_type = file.type
                extractor = None
                
                if file_type == PDF_MIME_TYPE:
                    extractor = PdfExtractor()
                elif file_type in IMAGE_MIME_TYPES:
                    extractor = ImageExtractor()
                elif "wordprocessingml" in file_type:
                    extractor = DocxExtractor()
                elif "presentationml" in file_type:
                    extractor = PptxExtractor()
                else:
                    st.warning(f"Skipping unsupported file: {file.name}")
                    continue
                    
                raw_text = extractor.extract_text(file.read())
                if not raw_text:
                    continue
                    
                bib_text = detect_bibliography_section(raw_text) or raw_text
                raw_citations = split_citations(bib_text)
                detected_style, _ = detect_style(raw_citations) if raw_citations else (None, 0.0)
                
                file_citations = []
                for raw_cit in raw_citations:
                    parsed = parse_citation(raw_cit, detected_style)
                    if parsed:
                        file_citations.append(parsed)
                
                all_citations.extend(file_citations)
                
                # Display individual results in expander
                with st.expander(f"📄 {file.name} ({len(file_citations)} citations)"):
                    if not file_citations:
                        st.info("No citations found.")
                    for j, c in enumerate(file_citations, 1):
                        st.write(f"{j}. {c.title or 'Unknown'} - {c.author_string}")
                        
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")
            
            # Update progress
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        st.success(f"Batch processing complete! Found {len(all_citations)} total citations.")
        
        st.divider()
        if all_citations:
            st.subheader("Bulk Export")
            render_export_panel(all_citations, key_prefix="batch")
