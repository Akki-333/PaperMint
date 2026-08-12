"""Main extraction page for the Streamlit UI."""


import streamlit as st

from papermint.config import IMAGE_MIME_TYPES, PDF_MIME_TYPE
from papermint.extractors import DocxExtractor, ImageExtractor, PdfExtractor, PptxExtractor
from papermint.models import CitationStyle, ExtractionResult
from papermint.parsers.bibliography_detector import detect_bibliography_section
from papermint.parsers.citation_parser import parse_citation
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.parsers.summarizer import summarize
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.export_panel import render_export_panel
from papermint.ui.components.file_uploader import render_file_uploader
from papermint.ui.components.progress import render_processing_steps


def _render_summary_tab(result: ExtractionResult) -> None:
    """Render an enhanced document summary tab."""
    if not result.summary or not result.summary.strip():
        st.info("No summary could be generated for this document.")
        return

    # Word and sentence counts from raw text
    word_count = len(result.raw_text.split())
    sentence_count = result.raw_text.count('.') + result.raw_text.count('?') + result.raw_text.count('!')
    page_est = max(1, word_count // 300)

    st.markdown(f"""
    <div class="summary-container">
        <div class="summary-heading">📝 Document Summary</div>
        <div class="summary-text">{result.summary}</div>
        <div class="summary-meta">
            <span class="summary-chip">📄 ~{page_est} page{'s' if page_est != 1 else ''}</span>
            <span class="summary-chip">📊 {word_count:,} words</span>
            <span class="summary-chip">📖 ~{sentence_count:,} sentences</span>
            <span class="summary-chip">📚 {result.citation_count} citation{'s' if result.citation_count != 1 else ''}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_raw_text_tab(raw_text: str) -> None:
    """Render a cleaner raw text tab with stats."""
    word_count = len(raw_text.split())
    char_count = len(raw_text)
    line_count = raw_text.count('\n') + 1

    st.markdown(f"""
    <div class="raw-text-stats">
        <span class="raw-stat">📝 {word_count:,} words</span>
        <span class="raw-stat">🔤 {char_count:,} characters</span>
        <span class="raw-stat">📄 {line_count:,} lines</span>
    </div>
    """, unsafe_allow_html=True)

    # Show the text in an expandable, searchable format
    with st.expander("📄 View Full Extracted Text", expanded=False):
        st.text_area(
            "Extracted text content",
            raw_text,
            height=400,
            disabled=True,
            label_visibility="collapsed"
        )

    # Show a cleaner preview
    preview_lines = raw_text.strip().split('\n')
    preview = '\n'.join(preview_lines[:30])
    if len(preview_lines) > 30:
        preview += "\n\n... (expand above to see full text)"

    st.markdown(f"""
    <div class="raw-text-container">{preview}</div>
    """, unsafe_allow_html=True)


def _render_citations_tab(citations: list) -> None:
    """Render the citations tab with filtering."""
    if not citations:
        st.info("No citations could be parsed from this document.")
        return

    # Filter controls
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input(
            "🔍 Filter citations",
            placeholder="Search by title, author, year...",
            key="cit_search",
            label_visibility="collapsed"
        )
    with col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Default Order", "Year (Newest)", "Year (Oldest)", "Confidence (High)", "Confidence (Low)"],
            key="cit_sort",
            label_visibility="collapsed"
        )

    # Apply filters
    filtered = citations
    if search:
        search_lower = search.lower()
        filtered = [
            c for c in citations
            if search_lower in (c.title or '').lower()
            or search_lower in (c.author_string or '').lower()
            or search_lower in (c.year or '')
        ]

    # Apply sorting
    if sort_option == "Year (Newest)":
        filtered = sorted(filtered, key=lambda c: c.year or "0", reverse=True)
    elif sort_option == "Year (Oldest)":
        filtered = sorted(filtered, key=lambda c: c.year or "9999")
    elif sort_option == "Confidence (High)":
        filtered = sorted(filtered, key=lambda c: c.confidence or 0.0, reverse=True)
    elif sort_option == "Confidence (Low)":
        filtered = sorted(filtered, key=lambda c: c.confidence or 0.0)

    # Show count
    if search and len(filtered) != len(citations):
        st.caption(f"Showing {len(filtered)} of {len(citations)} citations")

    # Render cards
    for i, citation in enumerate(filtered, 1):
        render_citation_card(citation, index=i)


def render() -> None:
    """Render the citation extraction page."""
    # Hero header
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">Extract Citations</div>
        <div class="hero-subtitle">Upload a document to extract, parse, and export its bibliography automatically</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = render_file_uploader(key="extract_upload", accept_multiple=False)

    force_parse = False
    if uploaded_file is not None:
        with st.expander("⚙️ Advanced Options", expanded=False):
            force_parse = st.checkbox(
                "Treat entire document as a bibliography",
                value=False,
                help="Bypass detection heuristics and force parse the entire text. Useful for annotated bibliographies or raw reference lists."
            )

        try:
            with st.spinner("Processing your document..."):
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
                bib_text = detect_bibliography_section(raw_text, force_parse=force_parse)

                parsed_citations = []
                detected_style = CitationStyle.UNKNOWN
                style_conf = 0.0

                if bib_text:
                    # Step 3: Split & Parse Citations
                    render_processing_steps(3)
                    raw_citations = split_citations(bib_text)

                    if raw_citations:
                        detected_style, style_conf = detect_style(raw_citations)

                    for raw_cit in raw_citations:
                        parsed_cit = parse_citation(raw_cit, detected_style)
                        if parsed_cit:
                            parsed_citations.append(parsed_cit)
                else:
                    # Skip parsing if no bibliography is found
                    render_processing_steps(3)
                    st.warning("⚠️ No structured bibliography detected in this document.")

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

            # Success message
            if result.citation_count > 0:
                st.success(f"✨ Extraction complete! Found **{result.citation_count}** citations from *{uploaded_file.name}*.")
            else:
                st.info(f"✨ Document processed: *{uploaded_file.name}*. Showing summary and raw text only.")

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
                style_name = result.detected_style.value.upper() if hasattr(result.detected_style, 'value') else str(result.detected_style)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5em; padding-top: 8px;">{style_name}</div>
                    <div class="metric-label">Detected Style</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                # Average confidence across all citations
                if parsed_citations:
                    avg_conf = sum(c.confidence for c in parsed_citations) / len(parsed_citations) * 100
                else:
                    avg_conf = 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_conf:.0f}%</div>
                    <div class="metric-label">Avg Confidence</div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

            if result.citation_count > 0:
                tab_citations, tab_summary, tab_raw = st.tabs(["📚 Citations", "📝 Summary", "📄 Raw Text"])
                with tab_citations:
                    _render_citations_tab(result.citations)
                with tab_summary:
                    _render_summary_tab(result)
                with tab_raw:
                    _render_raw_text_tab(result.raw_text)
                    
                # Export Panel
                st.divider()
                render_export_panel(result.citations, key_prefix="main")
            else:
                tab_summary, tab_raw = st.tabs(["📝 Summary", "📄 Raw Text"])
                with tab_summary:
                    _render_summary_tab(result)
                with tab_raw:
                    _render_raw_text_tab(result.raw_text)

        except Exception as e:
            st.error(f"An error occurred during processing: {e!s}")
