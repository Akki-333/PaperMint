"""Main extraction page for the Streamlit UI."""

import streamlit as st
import time

from papermint.extractors import PdfExtractor, ImageExtractor, DocxExtractor, PptxExtractor
from papermint.parsers.bibliography_detector import detect_bibliography_section
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.parsers.citation_parser import parse_citation
from papermint.parsers.summarizer import summarize
from papermint.models import ExtractionResult, CitationStyle

from papermint.config import IMAGE_MIME_TYPES, PDF_MIME_TYPE
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.file_uploader import render_file_uploader
from papermint.ui.components.export_panel import render_export_panel
from papermint.ui.components.progress import render_processing_steps

def render() -> None:
    """Render the citation extraction page."""
    st.title("📄 Extract Citations")
    st.markdown("Upload a document to extract and parse its bibliography automatically.")
    
    uploaded_file = render_file_uploader(key="extract_upload", accept_multiple=False)
    
    if uploaded_file is not None:
        try:
            with st.spinner("Extracting text..."):
                file_type = uploaded_file.type
                extractor = None
                
                # Step 1: Select Extractor
                render_processing_steps(1)
                
                if file_type == PDF_MIME_TYPE:
                    extractor = PdfExtractor()
                elif file_type in IMAGE_MIME_TYPES:
                    extractor = ImageExtractor()
                elif "wordprocessingml" in file_type:
                    extractor = DocxExtractor()
                elif "presentationml" in file_type:
                    extractor = PptxExtractor()
                else:
                    st.error(f"Unsupported file type: {file_type}")
                    return
                
                raw_text = extractor.extract_text(uploaded_file.read())
                
                if not raw_text or not raw_text.strip():
                    st.error("No text could be extracted from the uploaded document.")
                    return
                
                # Step 2: Detect Bibliography
                render_processing_steps(2)
                bib_text = detect_bibliography_section(raw_text)
                if not bib_text:
                    st.warning("Could not reliably detect a bibliography section. Proceeding with raw text.")
                    bib_text = raw_text
                
                # Step 3: Split & Parse Citations
                render_processing_steps(3)
                raw_citations = split_citations(bib_text)
                
                detected_style = CitationStyle.UNKNOWN
                style_conf = 0.0
                if raw_citations:
                    detected_style, style_conf = detect_style(raw_citations)
                
                parsed_citations = []
                for raw_cit in raw_citations:
                    parsed_cit = parse_citation(raw_cit, detected_style)
                    if parsed_cit:
                        parsed_citations.append(parsed_cit)
                
                # Generate Summary
                summary = summarize(raw_text)
                
                # Build Result Model
                result = ExtractionResult(
                    citations=parsed_citations,
                    raw_text=raw_text,
                    source_filename=uploaded_file.name,
                    detected_style=detected_style,
                    style_confidence=style_conf,
                    summary=summary,
                    page_count=0,
                    warnings=[]
                )
                
                # Step 4: Done
                render_processing_steps(4)
            
            # Display Results
            st.success(f"Extraction complete! Found {result.citation_count} citations.")
            
            # Metrics Row
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{result.citation_count}</div>
                    <div class="metric-label">Citations Found</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                style_name = result.detected_style.value if hasattr(result.detected_style, 'value') else str(result.detected_style)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5em; line-height: 1.3em; padding-top: 10px;">{style_name}</div>
                    <div class="metric-label">Detected Style</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                conf_pct = result.style_confidence * 100
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{conf_pct:.0f}%</div>
                    <div class="metric-label">Avg Confidence</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.divider()
            
            # Tabs for detailed view
            tab1, tab2, tab3 = st.tabs(["Citations", "Summary", "Raw Text"])
            
            with tab1:
                if not result.citations:
                    st.info("No citations could be parsed.")
                else:
                    for i, citation in enumerate(result.citations, 1):
                        render_citation_card(citation, index=i)
            
            with tab2:
                st.markdown("### Document Summary")
                st.write(result.summary)
                
            with tab3:
                st.markdown("### Extracted Text")
                st.text_area("Raw Text", result.raw_text, height=300, disabled=True)
                
            # Export Panel
            render_export_panel(result.citations, key_prefix="main")
            
        except Exception as e:
            st.error(f"An error occurred during processing: {str(e)}")
