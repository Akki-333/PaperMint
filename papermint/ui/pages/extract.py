"""The document analyzer page.

This page is presentation only. It captures the upload and the reader's
options, hands them to :class:`~papermint.pipeline.PipelineService`, keeps the
result in session state, and renders it. It contains no regular expressions,
no file decoding and no field extraction.

Keeping the result in session state matters for more than speed: Streamlit
reruns the whole script on every widget interaction, so without a cache,
typing in the search box would reprocess the document from scratch.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from papermint.config import RAW_TEXT_PREVIEW_LINES
from papermint.errors import PaperMintError
from papermint.models import Citation, DocumentKind, ExtractionResult
from papermint.pipeline import DocumentInput, PipelineOptions, PipelineService, PipelineStage
from papermint.ui.components.citation_browser import browser_keys, render_citation_browser
from papermint.ui.components.export_panel import render_export_panel, safe_filename
from papermint.ui.components.file_uploader import (
    read_upload,
    render_file_uploader,
    upload_signature,
)
from papermint.ui.components.primitives import (
    Stat,
    chip_row,
    definition_list,
    empty_state,
    notice,
    page_header,
    prose,
    section_header,
    source_block,
    stat_row,
)
from papermint.ui.components.progress import PipelineStepper, render_stepper
from papermint.ui.state import forget, restore, retain

logger = logging.getLogger(__name__)

_SIGNATURE_KEY = "pm_extract_signature"
_RESULT_KEY = "pm_extract_result"
_CITATIONS_KEY = "pm_extract_citations"

#: Widget namespace for this page's citation browser. The prefix is unchanged
#: from when the controls lived here, so a reader's remembered search text and
#: page number survive the move to the shared component.
_BROWSER_PREFIX = "pm_cit"

#: Widget values mirrored across page switches. Streamlit collects the state of
#: any widget it does not draw on a given run, so without this a glance at the
#: About page emptied the search box, the sort order and the reading mode.
_STICKY_KEYS = ("pm_summary_len", "pm_reading_mode", *browser_keys(_BROWSER_PREFIX))

#: Starting values, seeded into session state rather than passed to the widgets
#: as ``value=`` or ``index=``. Supplying both a literal default and a
#: session-state value makes Streamlit warn that the widget was set twice. The
#: browser seeds its own ordering, so only the summary slider is listed here.
_DEFAULTS: dict[str, object] = {
    "pm_summary_len": 5,
}

#: The reader's override of the classifier, mapped to
#: ``(force_parse, force_prose)``. Detection is autonomous, so "Detect
#: automatically" is the default and the only option most readers ever need.
#: The other two exist because a classifier that cannot be overruled leaves a
#: reader with no recourse when it is wrong.
_READING_MODES: dict[str, tuple[bool, bool]] = {
    "Detect automatically": (False, False),
    "Every line is a reference": (True, False),
    "There are no references": (False, True),
}


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------


def _run_pipeline(
    uploaded_file: Any, options: PipelineOptions, stepper: PipelineStepper
) -> ExtractionResult | None:
    """Process the upload, reporting progress and errors in the page.

    Args:
        uploaded_file: The Streamlit upload object.
        options: The reader's processing options.
        stepper: The live stage indicator.

    Returns:
        The result, or None when processing failed.
    """
    document = DocumentInput(
        filename=uploaded_file.name,
        data=read_upload(uploaded_file),
        mime_type=uploaded_file.type or "",
    )

    try:
        with st.spinner("Analysing the document…"):
            result = PipelineService().process_document(
                document, options, on_progress=stepper.update
            )
    except PaperMintError as err:
        stepper.fail(message=str(err))
        st.write("")
        notice(
            "This document could not be processed",
            str(err),
            tone="critical",
            details=[err.remedy] if err.remedy else None,
        )
        return None
    except Exception:
        logger.exception("Unexpected failure while processing %s", document.filename)
        stepper.fail(message="An unexpected error interrupted processing.")
        st.write("")
        notice(
            "Something went wrong",
            "An unexpected error interrupted processing. The details were written "
            "to the application log.",
            tone="critical",
        )
        return None

    stepper.finish()
    return result


def _ensure_result(
    uploaded_file: Any, options: PipelineOptions, stepper: PipelineStepper
) -> ExtractionResult | None:
    """Return the cached result for this upload, processing it if needed.

    Args:
        uploaded_file: The Streamlit upload object.
        options: The reader's processing options.
        stepper: The live stage indicator.

    Returns:
        The result, or None when processing failed.
    """
    signature = upload_signature(
        uploaded_file,
        options.force_parse,
        options.force_prose,
        options.summary_sentences,
    )

    if st.session_state.get(_SIGNATURE_KEY) == signature:
        stepper.finish()
        return st.session_state.get(_RESULT_KEY)

    result = _run_pipeline(uploaded_file, options, stepper)
    if result is None:
        st.session_state.pop(_SIGNATURE_KEY, None)
        st.session_state.pop(_RESULT_KEY, None)
        st.session_state.pop(_CITATIONS_KEY, None)
        return None

    st.session_state[_SIGNATURE_KEY] = signature
    st.session_state[_RESULT_KEY] = result
    st.session_state[_CITATIONS_KEY] = list(result.citations)
    return result


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------


def _render_verdict(result: ExtractionResult, citations: list[Citation]) -> None:
    """Explain what the pipeline concluded about the document.

    Args:
        result: The processed document.
        citations: The current citation list, including any reader edits.
    """
    if citations:
        notice(
            f"{len(citations)} references extracted from {result.source_filename}",
            f"{result.document_kind.label} · {result.detection_method.label}.",
            tone="positive",
        )
        return

    if result.discarded:
        notice(
            "This document does not appear to contain a bibliography",
            "A block of text was located where a reference list usually sits, but not "
            "one segment in it carried an author, a year, a venue or an identifier. "
            "Rather than present prose as though it were a reference list, PaperMint "
            "reported none.",
            tone="caution",
            details=[
                (
                    "If this really is a reference list, set How to read this document "
                    'to "Every line is a reference" under Options.'
                ),
            ],
        )
        return

    if result.document_kind is DocumentKind.NON_ACADEMIC:
        notice(
            "No bibliography in this document",
            "PaperMint found no references heading and no dense block of citations, "
            "so it did not invent any. The document summary and its full text are "
            "below.",
            tone="info",
            details=[
                (
                    "If this document is a reference list without a heading, set How to "
                    'read this document to "Every line is a reference" under Options.'
                ),
            ],
        )
        return

    notice(
        "A bibliography was located but no entries could be read",
        f"{result.detection_method.label}, yet the block could not be split into "
        "individual references.",
        tone="caution",
    )


def _render_headline_stats(result: ExtractionResult, citations: list[Citation]) -> None:
    """Render the four headline numbers for the run.

    Args:
        result: The processed document.
        citations: The current citation list.
    """
    average = sum(c.confidence for c in citations) / len(citations) if citations else 0.0
    flagged = sum(1 for c in citations if c.needs_review)

    stat_row(
        [
            Stat(
                "References",
                str(len(citations)),
                f"{flagged} need review" if flagged else "All complete",
                "library",
            ),
            Stat(
                "Style",
                result.detected_style.label,
                f"{result.style_confidence:.0%} confidence"
                if result.style_confidence
                else "Not determined",
                "quote",
                textual=True,
            ),
            Stat(
                "Field coverage",
                f"{average:.0%}",
                "Mean across all entries",
                "check",
            ),
            Stat(
                "Document",
                f"{result.stats.estimated_pages}",
                f"pages · {result.stats.word_count:,} words",
                "document",
            ),
        ]
    )


def _render_citations_tab(citations: list[Citation]) -> None:
    """Render the searchable, sortable, editable citation list.

    The controls themselves live in
    :func:`~papermint.ui.components.citation_browser.render_citation_browser`,
    because the batch page needs exactly the same four and a second copy of
    them would drift.

    Args:
        citations: The current citation list from session state.
    """
    edit = render_citation_browser(
        citations,
        scope="extract",
        key_prefix=_BROWSER_PREFIX,
        editable=True,
    )
    if edit is not None:
        original_index, updated = edit
        st.session_state[_CITATIONS_KEY][original_index] = updated
        st.rerun()


def _render_summary_tab(result: ExtractionResult) -> None:
    """Render the document summary and the detection reasoning.

    Args:
        result: The processed document.
    """
    stats = result.stats
    chip_row(
        [
            ("document", f"{stats.estimated_pages} pages"),
            ("hash", f"{stats.word_count:,} words"),
            ("quote", f"{stats.sentence_count:,} sentences"),
            ("clock", f"{stats.reading_minutes} min read"),
        ]
    )

    if result.summary.strip():
        section_header("Summary")
        prose(result.summary)
    else:
        empty_state(
            "No summary available",
            "This document has no narrative body to summarise.",
            icon_name="quote",
        )

    section_header("How this document was read")
    # The same four stages the run animated through, now at rest. It is drawn
    # without motion because this tab is redrawn on every interaction, and a
    # settled fact that re-animates becomes a distraction.
    render_stepper(PipelineStage.DONE, animated=False)
    st.write("")
    definition_list(
        [
            ("Document type", result.document_kind.label),
            ("Bibliography found by", result.detection_method.label),
            ("Citation style", result.detected_style.label),
            ("Processing time", f"{result.duration_ms:,} ms"),
            ("Source file", result.source_filename),
        ]
    )

    if result.warnings:
        with st.expander("Processing notes"):
            for note in result.warnings:
                st.caption(note)


def _render_source_tab(result: ExtractionResult) -> None:
    """Render the extracted source text.

    Args:
        result: The processed document.
    """
    stats = result.stats
    chip_row(
        [
            ("hash", f"{stats.word_count:,} words"),
            ("hash", f"{stats.character_count:,} characters"),
            ("layers", f"{stats.line_count:,} lines"),
        ]
    )

    lines = result.raw_text.split("\n")
    section_header(
        "Extracted text",
        f"First {min(RAW_TEXT_PREVIEW_LINES, len(lines))} lines",
    )
    source_block("\n".join(lines[:RAW_TEXT_PREVIEW_LINES]))

    if len(lines) > RAW_TEXT_PREVIEW_LINES:
        with st.expander(f"Show all {len(lines):,} lines"):
            st.text_area(
                "Full extracted text",
                result.raw_text,
                height=460,
                disabled=True,
                label_visibility="collapsed",
            )

    if result.bibliography_text:
        with st.expander("Show the isolated bibliography block"):
            source_block(result.bibliography_text)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def _render_results(result: ExtractionResult, citations: list[Citation]) -> None:
    """Render the verdict, the headline numbers and the three result tabs.

    Args:
        result: The processed document.
        citations: The current citation list, including any reader edits.
    """
    _render_verdict(result, citations)
    st.write("")
    _render_headline_stats(result, citations)
    st.write("")

    if citations:
        tab_citations, tab_summary, tab_source = st.tabs(["References", "Summary", "Source text"])
        with tab_citations:
            _render_citations_tab(citations)
        with tab_summary:
            _render_summary_tab(result)
        with tab_source:
            _render_source_tab(result)

        st.divider()
        render_export_panel(
            citations,
            key_prefix="extract",
            default_name=safe_filename(result.source_filename.rsplit(".", 1)[0]),
        )
        from papermint.ui.navigation import page

        st.caption(
            "These references stay loaded while you move around the application. "
            "Open Reference formatter to set them in APA, MLA, IEEE or Chicago."
        )
        st.page_link(
            page("styles"),
            label="Format references in APA, MLA, IEEE or Chicago",
            icon=":material/format_quote:",
        )
        return

    tab_summary, tab_source = st.tabs(["Summary", "Source text"])
    with tab_summary:
        _render_summary_tab(result)
    with tab_source:
        _render_source_tab(result)


def _render_restored(result: ExtractionResult) -> None:
    """Explain that the results on screen came from a document already read.

    The upload control cannot hold its file across a page switch, because
    Streamlit collects the state of any widget it did not draw. The parsed
    result outlives that, so it is shown rather than thrown away, and the
    reader is told plainly why the dropzone above it is empty.

    Args:
        result: The cached result being redisplayed.
    """
    left, right = st.columns([4, 1])
    left.caption(
        f"Showing the last document you analysed, {result.source_filename}. "
        "Drop another file above to replace it."
    )
    if right.button("Start over", use_container_width=True, key="pm_extract_reset"):
        forget(_SIGNATURE_KEY, _RESULT_KEY, _CITATIONS_KEY, *_STICKY_KEYS)
        st.rerun()


def render() -> None:
    """Render the document analyzer page."""
    restore(*_STICKY_KEYS)
    for key, value in _DEFAULTS.items():
        st.session_state.setdefault(key, value)

    page_header(
        "Document analyzer",
        "Upload a paper, thesis or bibliography. PaperMint collects every "
        "reference block it can find, parses each entry into structured "
        "fields, and reports how much of every one it could actually read.",
        eyebrow="Analyze",
        eyebrow_icon="document",
    )

    uploaded_file = render_file_uploader(key="extract_upload", accept_multiple=False)
    cached: ExtractionResult | None = st.session_state.get(_RESULT_KEY)

    if uploaded_file is None:
        if cached is None:
            empty_state(
                "Ready when you are",
                "Drop a document above to begin. Everything is processed on this "
                "machine; nothing is uploaded anywhere.",
                icon_name="document",
            )
            return
        _render_restored(cached)
        render_stepper(PipelineStage.DONE, animated=False)
        _render_results(cached, st.session_state.get(_CITATIONS_KEY, []))
        retain(*_STICKY_KEYS)
        return

    with st.expander("Options"):
        summary_sentences = st.slider(
            "Summary length",
            min_value=3,
            max_value=10,
            help="Number of sentences in the document summary.",
            key="pm_summary_len",
        )
        reading = st.radio(
            "How to read this document",
            options=list(_READING_MODES),
            help=(
                "PaperMint classifies the document itself. Override this only when "
                "the verdict below is wrong."
            ),
            key="pm_reading_mode",
        )

    force_parse, force_prose = _READING_MODES[reading]
    options = PipelineOptions(
        force_parse=force_parse,
        force_prose=force_prose,
        summary_sentences=summary_sentences,
    )
    stepper = PipelineStepper(slot=st.empty())
    result = _ensure_result(uploaded_file, options, stepper)
    if result is None:
        return

    _render_results(result, st.session_state.get(_CITATIONS_KEY, []))
    retain(*_STICKY_KEYS)


__all__ = ["render"]
