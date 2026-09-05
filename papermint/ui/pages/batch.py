"""The batch processing page.

Several documents are handed to the pipeline in one call. A failure in any one
file is recorded against that file and the run continues, so a single corrupt
PDF cannot discard an entire literature review.

Results are cached against a digest of the uploaded set, so moving between
documents does not reprocess anything.

**Why this page is a workbench rather than a list.** The first version stacked
one expander per file and put the merged export underneath all of them. Two
things followed. Opening a file with 163 references dropped 163 cards into the
page in one go, with no search, no ordering and no paging, so finding one
entry meant scrolling through all of them. And the export — the thing most
readers came for — sat below every expanded file, which on a five-file run put
it thousands of pixels down.

So the run is now a switcher and a pane. The rail on the left names every file
with its outcome, one click puts that document in the pane on the right, and
the pane carries that document's own search, ordering, paging and export. The
merged library and its export live in a sibling tab, one click from the top of
the results, never below them.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from papermint.config import RAW_TEXT_PREVIEW_LINES
from papermint.models import BatchFileResult, BatchResult
from papermint.pipeline import DocumentInput, PipelineOptions, PipelineService
from papermint.ui.components.citation_browser import browser_keys, render_citation_browser
from papermint.ui.components.export_panel import (
    render_compact_export,
    render_export_panel,
    safe_filename,
)
from papermint.ui.components.file_uploader import (
    read_upload,
    render_file_uploader,
    upload_signature,
)
from papermint.ui.components.primitives import (
    NoticeTone,
    Stat,
    document_header,
    empty_state,
    micro_note,
    notice,
    page_header,
    section_header,
    source_block,
    stat_row,
)
from papermint.ui.html import clamp
from papermint.ui.state import forget, restore, retain

logger = logging.getLogger(__name__)

_SIGNATURE_KEY = "pm_batch_signature"
_RESULT_KEY = "pm_batch_result"

#: Which file the pane is showing. Not a widget key, so Streamlit never
#: collects it and it needs no shadow copy.
_SELECTED_KEY = "pm_batch_file"

#: Widget namespaces for the two citation browsers this page renders.
_DOC_PREFIX = "pm_batch_doc"
_LIB_PREFIX = "pm_batch_lib"

#: Widget values mirrored across page switches, for the same reason as on the
#: analyzer page: Streamlit collects the state of any widget it did not draw.
_STICKY_KEYS = (
    "pm_batch_reading_mode",
    *browser_keys(_DOC_PREFIX),
    *browser_keys(_LIB_PREFIX),
)

#: Above this many files the switcher becomes its own scroll region, so the
#: rail can never be taller than a screen and the pane beside it stays in view.
_RAIL_SCROLLS_ABOVE = 7

#: Height of that scroll region, in pixels.
_RAIL_HEIGHT = 460

#: How much of a filename the rail shows before eliding it. The full name is
#: in the button's tooltip and at the head of the pane.
_RAIL_NAME_CHARS = 30


#: The reader's override of the classifier, applied to every file in the batch.
#: Each file is still characterised on its own merits under the default, so a
#: mixed upload of papers, catalogues and prose needs no setting at all.
_READING_MODES: dict[str, tuple[bool, bool]] = {
    "Detect each file automatically": (False, False),
    "Every file is a reference list": (True, False),
    "No file has references": (False, True),
}


def _batch_signature(files: list[Any], force_parse: bool, force_prose: bool) -> str:
    """Build a cache key covering every uploaded file and the options.

    Args:
        files: The uploaded files.
        force_parse: The bibliography override.
        force_prose: The no-bibliography override.

    Returns:
        A digest identifying this batch.
    """
    return "|".join(upload_signature(f, force_parse, force_prose) for f in files)


def _run_batch(files: list[Any], options: PipelineOptions) -> BatchResult:
    """Process every uploaded file, reporting progress as it goes.

    Args:
        files: The uploaded files.
        options: The processing options applied to all of them.

    Returns:
        The aggregated batch result.
    """
    documents = [
        DocumentInput(filename=f.name, data=read_upload(f), mime_type=f.type or "") for f in files
    ]

    progress = st.progress(0.0, text="Starting…")

    def report(index: int, total: int, filename: str) -> None:
        progress.progress(index / total, text=f"Reading {filename} ({index + 1} of {total})")

    result = PipelineService().process_batch(documents, options, on_file=report)
    progress.empty()
    return result


def _ensure_result(files: list[Any], options: PipelineOptions) -> BatchResult:
    """Return the cached batch result, running the batch if needed.

    Args:
        files: The uploaded files.
        options: The processing options.

    Returns:
        The batch result.
    """
    signature = _batch_signature(files, options.force_parse, options.force_prose)
    if st.session_state.get(_SIGNATURE_KEY) == signature:
        return st.session_state[_RESULT_KEY]

    result = _run_batch(files, options)
    st.session_state[_SIGNATURE_KEY] = signature
    st.session_state[_RESULT_KEY] = result
    # A new run invalidates the old selection: file three of the previous set
    # is not file three of this one.
    st.session_state[_SELECTED_KEY] = 0
    return result


# ---------------------------------------------------------------------------
# The run at a glance
# ---------------------------------------------------------------------------


def _render_summary(result: BatchResult) -> None:
    """Render the headline numbers for the run.

    Args:
        result: The aggregated batch result.
    """
    if result.error_count:
        notice(
            f"{result.success_count} of {result.file_count} files processed",
            f"{result.error_count} could not be read. Every other file completed "
            "normally, and each one is listed under Documents with its own "
            "references.",
            tone="caution",
        )
    else:
        notice(
            f"All {result.file_count} files processed",
            f"{result.citation_count} references collected in "
            f"{result.duration_ms / 1000:.1f} seconds.",
            tone="positive",
        )

    flagged = sum(1 for c in result.citations if c.needs_review)
    stat_row(
        [
            Stat(
                "Files",
                str(result.file_count),
                f"{result.error_count} failed",
                "layers",
            ),
            Stat(
                "References",
                str(result.citation_count),
                f"{flagged} need review" if flagged else "All complete",
                "library",
            ),
            Stat(
                "Field coverage",
                f"{result.average_confidence:.0%}",
                "Mean across the run",
                "check",
            ),
            Stat(
                "Elapsed",
                f"{result.duration_ms / 1000:.1f}s",
                f"{result.duration_ms // max(1, result.file_count)} ms per file",
                "clock",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# The document switcher
# ---------------------------------------------------------------------------


def _outcome(entry: BatchFileResult) -> tuple[str, str, NoticeTone]:
    """Describe one file's outcome for the switcher.

    Args:
        entry: The file's result.

    Returns:
        A ``(material icon, one-line note, tone)`` triple.
    """
    if not entry.succeeded:
        return ":material/error:", "Could not be read", "critical"

    document = entry.result
    if document is None or not document.citations:
        return ":material/description:", "No bibliography", "neutral"

    found = document.citation_count
    plural = "" if found == 1 else "s"
    note = f"{found} reference{plural} · {document.average_confidence:.0%} read"
    return ":material/library_books:", note, "neutral"


def _selected_index(result: BatchResult) -> int:
    """Return the index of the file the pane should show.

    A remembered selection can outlive the run it belonged to, so it is
    clamped rather than trusted.

    Args:
        result: The aggregated batch result.

    Returns:
        A valid index into ``result.files``.
    """
    current = st.session_state.get(_SELECTED_KEY, 0)
    if not isinstance(current, int) or not 0 <= current < result.file_count:
        current = 0
    st.session_state[_SELECTED_KEY] = current
    return current


def _render_rail(result: BatchResult, current: int) -> None:
    """Render the file switcher.

    Each entry is a full-width button carrying the file's name and, beneath
    it, one line saying how that file turned out. The selected entry is marked
    by its container's key, which is what the stylesheet targets: Streamlit
    gives a keyed container an ``st-key-`` class, and a page cannot otherwise
    style one widget differently from its siblings.

    Args:
        result: The aggregated batch result.
        current: The index of the selected file.
    """
    # Deliberately not a section heading: its top margin would drop the rail
    # a step below the document name it sits beside, and the run's own file
    # count is already in the statistics above.
    files = result.file_count
    micro_note(f"{files} file{'' if files == 1 else 's'} in this run")

    scrolls = result.file_count > _RAIL_SCROLLS_ABOVE
    rail = (
        st.container(height=_RAIL_HEIGHT, border=False, key="pmrail")
        if scrolls
        else st.container(key="pmrail")
    )

    with rail:
        for index, entry in enumerate(result.files):
            glyph, note, tone = _outcome(entry)
            state = "on" if index == current else "off"
            with st.container(key=f"pmfile-{state}-{index}"):
                if st.button(
                    clamp(entry.filename, _RAIL_NAME_CHARS),
                    key=f"pm_batch_pick_{index}",
                    icon=glyph,
                    use_container_width=True,
                    help=entry.filename,
                ):
                    st.session_state[_SELECTED_KEY] = index
                    st.rerun()
                micro_note(note, tone=tone)


# ---------------------------------------------------------------------------
# The document pane
# ---------------------------------------------------------------------------


def _render_pane(entry: BatchFileResult) -> None:
    """Render everything about the one file the reader chose.

    Args:
        entry: The selected file's result.
    """
    document = entry.result
    citations = list(document.citations) if document else []

    head, actions = st.columns([5, 2])
    with head:
        chips: list[tuple[str, str]] = []
        if document is not None:
            chips = [
                ("document", document.document_kind.label),
                ("quote", document.detected_style.label),
                ("search", document.detection_method.label),
                ("check", f"{document.average_confidence:.0%} field coverage"),
            ]
        document_header(entry.filename, chips)
    with actions:
        if citations:
            with st.popover("Export this file", use_container_width=True):
                render_compact_export(
                    citations,
                    key_prefix="pm_batch_doc_export",
                    default_name=safe_filename(entry.filename.rsplit(".", 1)[0]),
                )

    if not entry.succeeded:
        notice("This file was skipped", entry.error, tone="critical")
        return

    if document is None:
        notice("Nothing was returned for this file", tone="critical")
        return

    if citations:
        render_citation_browser(
            citations,
            scope="batchdoc",
            key_prefix=_DOC_PREFIX,
        )
    else:
        notice(
            "No references in this file",
            f"PaperMint read it as {document.document_kind.label.lower()} and found no "
            "reference list, so it reported none rather than presenting prose as "
            "citations.",
            tone="info",
            details=[
                (
                    "If this file is a reference list, set How to read these documents "
                    'to "Every file is a reference list" under Options.'
                ),
            ],
        )

    if document.raw_text.strip():
        lines = document.raw_text.split("\n")
        shown = min(RAW_TEXT_PREVIEW_LINES, len(lines))
        with st.expander(f"Extracted text — first {shown} lines"):
            source_block("\n".join(lines[:RAW_TEXT_PREVIEW_LINES]))

    if document.warnings:
        with st.expander("Processing notes"):
            for line in document.warnings:
                st.caption(line)


def _render_library(result: BatchResult) -> None:
    """Render the merged export and the whole run's references.

    The export comes first deliberately. It is what most readers open the
    batch page for, and putting it under the list is what made them scroll to
    the bottom of the page to find it.

    Args:
        result: The aggregated batch result.
    """
    citations = result.citations
    if not citations:
        empty_state(
            "Nothing to export yet",
            "No file in this run produced a reference the parser could read.",
            icon_name="download",
        )
        return

    render_export_panel(
        citations,
        key_prefix="batch",
        default_name="merged_bibliography",
        title="Merged export",
    )
    st.divider()
    sources = sum(1 for f in result.files if f.citation_count)
    section_header(
        "Every reference in this run",
        f"from {sources} file{'' if sources == 1 else 's'}",
    )
    render_citation_browser(
        citations,
        scope="batchlib",
        key_prefix=_LIB_PREFIX,
        show_source=True,
    )


def _render_run(result: BatchResult) -> None:
    """Render one completed batch run.

    Args:
        result: The aggregated batch result.
    """
    _render_summary(result)
    st.write("")

    documents_tab, library_tab = st.tabs(["Documents", "Merged export"])
    with documents_tab:
        if not result.files:
            empty_state("Nothing in this run", "No files were processed.", icon_name="layers")
        else:
            current = _selected_index(result)
            rail, pane = st.columns([1, 2.4], gap="medium")
            with rail:
                _render_rail(result, current)
            with pane:
                _render_pane(result.files[current])
    with library_tab:
        _render_library(result)


def render() -> None:
    """Render the batch processing page."""
    restore(*_STICKY_KEYS)

    page_header(
        "Batch processing",
        "Process a whole reading list at once. Open any document to read its "
        "references on their own, or take the merged bibliography for the "
        "entire run. Files that cannot be read are reported individually and "
        "never abort the run.",
        eyebrow="Batch",
        eyebrow_icon="layers",
    )

    uploaded_files = render_file_uploader(key="batch_upload", accept_multiple=True)
    cached: BatchResult | None = st.session_state.get(_RESULT_KEY)

    if not uploaded_files:
        if cached is None:
            empty_state(
                "No files selected",
                "Add several documents above to build a combined bibliography.",
                icon_name="layers",
            )
            return
        # The uploader cannot hold its files across a page switch, but the run
        # itself outlives that, so it is shown rather than discarded.
        left, right = st.columns([4, 1])
        left.caption(
            f"Showing your last run of {cached.file_count} files. "
            "Add more documents above to start a new one."
        )
        if right.button("Start over", use_container_width=True, key="pm_batch_reset"):
            forget(_SIGNATURE_KEY, _RESULT_KEY, _SELECTED_KEY, *_STICKY_KEYS)
            st.rerun()
        _render_run(cached)
        retain(*_STICKY_KEYS)
        return

    with st.expander("Options"):
        reading = st.radio(
            "How to read these documents",
            options=list(_READING_MODES),
            help=(
                "Each file is classified on its own merits, so a mixed batch of "
                "papers, catalogues and prose needs no setting here. Override only "
                "when a document's verdict is wrong."
            ),
            key="pm_batch_reading_mode",
        )

    force_parse, force_prose = _READING_MODES[reading]
    result = _ensure_result(
        list(uploaded_files),
        PipelineOptions(force_parse=force_parse, force_prose=force_prose),
    )

    _render_run(result)
    retain(*_STICKY_KEYS)


__all__ = ["render"]
