"""The export panel.

Formats are declared once, as a table, so adding a format is a one-line change
rather than another branch in an if-chain. Serialisation runs inside a guard
that converts any failure into an :class:`~papermint.errors.ExportError`, so a
single unserialisable citation reports itself instead of tearing down the page.

The previous implementation opened a ``<div class="export-section">`` in one
``st.markdown`` call and closed it in another. Streamlit renders each call as
an isolated DOM node, so that wrapper never contained anything; the panel now
relies on real layout containers instead.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import streamlit as st

from papermint.errors import ExportError
from papermint.exporters import (
    bibtex_exporter,
    csv_exporter,
    docx_exporter,
    pdf_exporter,
    ris_exporter,
)
from papermint.models import Citation
from papermint.ui.components.primitives import section_header

logger = logging.getLogger(__name__)

#: Characters that are unsafe in a download filename.
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class ExportFormat:
    """One selectable output format.

    Attributes:
        label: The name shown in the picker.
        extension: The file extension, including the dot.
        mime: The MIME type sent with the download.
        serialise: Callable turning citations into bytes or text.
        note: A short line explaining what the format is for.
        previewable: Whether the payload is text that can be shown inline.
    """

    label: str
    extension: str
    mime: str
    serialise: Callable[[list[Citation]], Any]
    note: str
    previewable: bool = False


#: Every format the panel offers, in the order they appear.
EXPORT_FORMATS: tuple[ExportFormat, ...] = (
    ExportFormat(
        "BibTeX",
        ".bib",
        "application/x-bibtex",
        bibtex_exporter.export_bibtex,
        "For LaTeX and Overleaf.",
        previewable=True,
    ),
    ExportFormat(
        "RIS",
        ".ris",
        "application/x-research-info-systems",
        ris_exporter.export_ris,
        "For Zotero, Mendeley and EndNote.",
        previewable=True,
    ),
    ExportFormat(
        "CSV",
        ".csv",
        "text/csv",
        csv_exporter.export_csv,
        "For spreadsheets and data analysis.",
        previewable=True,
    ),
    ExportFormat(
        "Excel",
        ".xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        csv_exporter.export_excel,
        "A formatted workbook.",
    ),
    ExportFormat(
        "Word",
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        docx_exporter.export_docx,
        "A formatted reference list.",
    ),
    ExportFormat(
        "PDF",
        ".pdf",
        "application/pdf",
        pdf_exporter.export_pdf,
        "A printable reference list.",
    ),
)

_BY_LABEL: dict[str, ExportFormat] = {fmt.label: fmt for fmt in EXPORT_FORMATS}


def safe_filename(stem: str, fallback: str = "citations") -> str:
    """Reduce arbitrary text to a filename-safe stem.

    Args:
        stem: The proposed name, typically taken from the source document.
        fallback: Used when nothing usable survives.

    Returns:
        A filename stem containing only letters, digits, dots, dashes and
        underscores.
    """
    cleaned = _UNSAFE_FILENAME.sub("_", stem.strip()).strip("._-")
    return cleaned[:80] or fallback


def _serialise(fmt: ExportFormat, citations: list[Citation]) -> Any:
    """Serialise citations, converting any failure into an export error.

    Args:
        fmt: The chosen format.
        citations: The citations to write.

    Returns:
        The payload accepted by ``st.download_button``.

    Raises:
        ExportError: If serialisation fails for any reason.
    """
    try:
        return fmt.serialise(citations)
    except Exception as exc:
        logger.exception("Export to %s failed", fmt.label)
        raise ExportError(
            f"These citations could not be written as {fmt.label}: {exc}",
            remedy="Try a different format, or correct the flagged entries first.",
        ) from exc


def render_compact_export(
    citations: list[Citation],
    *,
    key_prefix: str,
    default_name: str,
) -> None:
    """Render a two-control export for a narrow container.

    The full panel needs the page's width: it lays its format picker and file
    name field out side by side and offers an inline preview behind an
    expander, which Streamlit refuses to nest inside another expander. This
    variant stacks a picker and a download button, so it fits inside a popover
    beside a document's heading and puts that document's own references one
    click away from the top of the pane.

    Args:
        citations: The citations to export.
        key_prefix: Prefix for widget keys, so several exports can coexist.
        default_name: The filename stem, taken from the source document.
    """
    if not citations:
        return

    st.caption(f"{len(citations)} references from this document.")
    label = st.selectbox(
        "Format",
        options=[fmt.label for fmt in EXPORT_FORMATS],
        key=f"{key_prefix}_format",
    )
    fmt = _BY_LABEL[label]
    st.caption(fmt.note)

    try:
        payload = _serialise(fmt, citations)
    except ExportError as err:
        st.error(str(err))
        return

    st.download_button(
        label=f"Download {fmt.label}",
        data=payload,
        file_name=f"{safe_filename(default_name)}{fmt.extension}",
        mime=fmt.mime,
        key=f"{key_prefix}_btn",
        use_container_width=True,
        type="primary",
    )


def render_export_panel(
    citations: list[Citation],
    key_prefix: str = "export",
    *,
    default_name: str = "citations",
    title: str = "Export",
) -> None:
    """Render the export panel with format selection and a download button.

    Args:
        citations: The citations to export.
        key_prefix: Prefix for widget keys, so several panels can coexist.
        default_name: The suggested filename stem.
        title: The section heading.
    """
    if not citations:
        return

    flagged = sum(1 for c in citations if c.needs_review)
    note = f"{len(citations)} entries"
    if flagged:
        note += f" · {flagged} flagged for review"
    section_header(title, note)

    picker, namer = st.columns([2, 3])
    with picker:
        label = st.selectbox(
            "Format",
            options=[fmt.label for fmt in EXPORT_FORMATS],
            key=f"{key_prefix}_format",
        )
    fmt = _BY_LABEL[label]

    with namer:
        stem = st.text_input(
            "File name",
            value=safe_filename(default_name),
            key=f"{key_prefix}_filename",
            help=fmt.note,
        )

    try:
        payload = _serialise(fmt, citations)
    except ExportError as err:
        st.error(str(err))
        if err.remedy:
            st.caption(err.remedy)
        return

    st.download_button(
        label=f"Download {fmt.label}",
        data=payload,
        file_name=f"{safe_filename(stem, default_name)}{fmt.extension}",
        mime=fmt.mime,
        key=f"{key_prefix}_btn",
        use_container_width=True,
        type="primary",
    )

    if fmt.previewable and isinstance(payload, str):
        with st.expander(f"Preview the {fmt.label} output"):
            language = "bibtex" if fmt.label == "BibTeX" else None
            st.code(payload[:8000], language=language)
            if len(payload) > 8000:
                st.caption("Preview truncated. The download contains every entry.")


__all__ = [
    "EXPORT_FORMATS",
    "ExportFormat",
    "render_compact_export",
    "render_export_panel",
    "safe_filename",
]
