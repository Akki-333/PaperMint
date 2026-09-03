"""The batch processing page.

Several documents are handed to the pipeline in one call. A failure in any one
file is recorded against that file and the run continues, so a single corrupt
PDF cannot discard an entire literature review.

Results are cached against a digest of the uploaded set, so browsing the
per-file accordions does not reprocess anything.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from papermint.models import BatchResult
from papermint.pipeline import DocumentInput, PipelineOptions, PipelineService
from papermint.ui.components.citation_card import render_citation_list
from papermint.ui.components.export_panel import render_export_panel
from papermint.ui.components.file_uploader import (
    read_upload,
    render_file_uploader,
    upload_signature,
)
from papermint.ui.components.primitives import (
    Stat,
    empty_state,
    notice,
    page_header,
    section_header,
    stat_row,
)

logger = logging.getLogger(__name__)

_SIGNATURE_KEY = "pm_batch_signature"
_RESULT_KEY = "pm_batch_result"


def _batch_signature(files: list[Any], force_parse: bool) -> str:
    """Build a cache key covering every uploaded file and the options.

    Args:
        files: The uploaded files.
        force_parse: The bibliography override.

    Returns:
        A digest identifying this batch.
    """
    return "|".join(upload_signature(f, force_parse) for f in files)


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
    signature = _batch_signature(files, options.force_parse)
    if st.session_state.get(_SIGNATURE_KEY) == signature:
        return st.session_state[_RESULT_KEY]

    result = _run_batch(files, options)
    st.session_state[_SIGNATURE_KEY] = signature
    st.session_state[_RESULT_KEY] = result
    return result


def _render_summary(result: BatchResult) -> None:
    """Render the headline numbers for the run.

    Args:
        result: The aggregated batch result.
    """
    if result.error_count:
        notice(
            f"{result.success_count} of {result.file_count} files processed",
            f"{result.error_count} could not be read. Every other file completed "
            "normally and its references are included below.",
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


def _render_files(result: BatchResult) -> None:
    """Render one expandable panel per processed file.

    Args:
        result: The aggregated batch result.
    """
    section_header("Results by file")

    for position, entry in enumerate(result.files):
        if not entry.succeeded:
            label = f"{entry.filename} — could not be read"
        elif entry.citation_count:
            label = f"{entry.filename} — {entry.citation_count} references"
        else:
            label = f"{entry.filename} — no bibliography"

        with st.expander(label):
            if not entry.succeeded:
                notice("This file was skipped", entry.error, tone="critical")
                continue

            document = entry.result
            if document is None or not document.citations:
                detail = ""
                if document is not None:
                    detail = f"{document.document_kind.label} · {document.detection_method.label}"
                notice("No references in this file", detail, tone="info")
                continue

            st.caption(
                f"{document.document_kind.label} · {document.detected_style.label} · "
                f"{document.detection_method.label}"
            )
            render_citation_list(document.citations, scope=f"batch{position}")


def render() -> None:
    """Render the batch processing page."""
    page_header(
        "Batch processing",
        "Process a whole reading list at once and export one merged "
        "bibliography. Files that cannot be read are reported individually "
        "and never abort the run.",
        eyebrow="Batch",
        eyebrow_icon="layers",
    )

    uploaded_files = render_file_uploader(key="batch_upload", accept_multiple=True)

    if not uploaded_files:
        empty_state(
            "No files selected",
            "Add several documents above to build a combined bibliography.",
            icon_name="layers",
        )
        return

    with st.expander("Options"):
        force_parse = st.checkbox(
            "Treat every document as a bibliography",
            value=False,
            help=(
                "Applies to all files in this batch. Use it when the set consists "
                "of reference lists rather than papers."
            ),
            key="pm_batch_force",
        )

    result = _ensure_result(list(uploaded_files), PipelineOptions(force_parse=force_parse))

    _render_summary(result)
    st.write("")
    _render_files(result)

    if result.citations:
        st.divider()
        render_export_panel(
            result.citations,
            key_prefix="batch",
            default_name="merged_bibliography",
            title="Merged export",
        )


__all__ = ["render"]
