"""Batch processing page for the Streamlit UI."""

import streamlit as st

from papermint.config import IMAGE_MIME_TYPES, PDF_MIME_TYPE
from papermint.extractors import DocxExtractor, ImageExtractor, PdfExtractor, PptxExtractor
from papermint.models import CitationStyle
from papermint.parsers.bibliography_detector import detect_bibliography_section
from papermint.parsers.citation_parser import parse_citation
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.export_panel import render_export_panel
from papermint.ui.components.file_uploader import render_file_uploader


def render() -> None:
    """Render the batch processing page."""
    # Hero header
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">Batch Processing</div>
        <div class="hero-subtitle">Upload multiple documents to extract citations in bulk</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = render_file_uploader(key="batch_upload", accept_multiple=True)

    if uploaded_files:
        st.markdown(f"**📁 Processing {len(uploaded_files)} file{'s' if len(uploaded_files) != 1 else ''}...**")

        progress_bar = st.progress(0)
        all_citations = []
        file_results = []

        for i, file in enumerate(uploaded_files):
            try:
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
                    file_results.append((file.name, [], "No text extracted"))
                    continue

                bib_text = detect_bibliography_section(raw_text) or raw_text
                raw_citations = split_citations(bib_text)
                detected_style = CitationStyle.UNKNOWN
                if raw_citations:
                    detected_style, _ = detect_style(raw_citations)

                file_citations = []
                for raw_cit in raw_citations:
                    parsed = parse_citation(raw_cit, detected_style)
                    if parsed:
                        file_citations.append(parsed)

                all_citations.extend(file_citations)
                file_results.append((file.name, file_citations, None))

            except Exception as e:
                file_results.append((file.name, [], str(e)))

            progress_bar.progress((i + 1) / len(uploaded_files))

        # Summary metrics
        st.success(f"✨ Batch processing complete! Found **{len(all_citations)}** total citations across **{len(uploaded_files)}** files.")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(uploaded_files)}</div>
                <div class="metric-label">Files Processed</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(all_citations)}</div>
                <div class="metric-label">Total Citations</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            errors = sum(1 for _, _, err in file_results if err)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{"✅" if errors == 0 else errors}</div>
                <div class="metric-label">{"All Clear" if errors == 0 else "Errors"}</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Individual file results
        st.markdown("### 📄 Results by File")

        for fname, citations, error in file_results:
            count_label = f"{len(citations)} citation{'s' if len(citations) != 1 else ''}" if not error else "⚠️ Error"

            with st.expander(f"📄 **{fname}** — {count_label}"):
                if error:
                    st.error(f"Error processing this file: {error}")
                elif not citations:
                    st.info("No citations found in this document.")
                else:
                    for j, c in enumerate(citations, 1):
                        render_citation_card(c, index=j)

        # Bulk export
        if all_citations:
            st.divider()
            st.markdown("### 📥 Bulk Export")
            render_export_panel(all_citations, key_prefix="batch")
