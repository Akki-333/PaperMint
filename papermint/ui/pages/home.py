"""The dashboard page.

The home page answers three questions before a reader uploads anything: what
this tool does, what it will do with the particular document they have, and
where to go next. The third is answered with real navigation links rather than
an instruction to look at the sidebar.
"""

from __future__ import annotations

import streamlit as st

from papermint.config import APP_NAME
from papermint.pipeline import accepted_formats
from papermint.ui.components.primitives import (
    definition_list,
    page_header,
    section_header,
    tile_grid,
)

#: What the pipeline does with each category of document.
_BEHAVIOURS: tuple[tuple[str, str], ...] = (
    (
        "Research paper",
        (
            "Isolates the references section, detects the citation style, and parses "
            "every entry into structured fields."
        ),
    ),
    (
        "Annotated bibliography",
        (
            "Separates each citation header from the annotation paragraphs beneath it, "
            "so quoted phrases in the commentary never become the title."
        ),
    ),
    (
        "Reference list with no heading",
        (
            "Locates the reference block by citation density, working backwards from "
            "the end of the document."
        ),
    ),
    (
        "General document",
        (
            "Reports that no bibliography exists and produces a summary instead. No "
            "citations are invented."
        ),
    ),
)

#: What the interface guarantees about its own output.
_PRINCIPLES: tuple[tuple[str, str], ...] = (
    (
        "Nothing is guessed",
        (
            "A field that cannot be read confidently is left empty and listed as "
            "missing, rather than filled with a plausible fragment."
        ),
    ),
    (
        "Every entry is scored",
        (
            "Each reference carries a field-coverage score, so an incomplete parse is "
            "visible at a glance instead of hiding among good ones."
        ),
    ),
    (
        "Corrections are yours to make",
        (
            "Any field can be edited inline before export, and the score updates to "
            "match what you entered."
        ),
    ),
)


def render() -> None:
    """Render the home dashboard page."""
    # Imported here rather than at module scope: navigation builds the page
    # objects from this module's render function, so a top-level import would
    # be circular.
    from papermint.ui.navigation import page

    page_header(
        APP_NAME,
        "Turn academic documents into structured, exportable bibliographic "
        "records. Every field is extracted deterministically, and every entry "
        "reports how much of it could actually be read.",
        eyebrow="Overview",
        eyebrow_icon="leaf",
    )

    section_header("Start here")
    tile_grid(
        [
            (
                "document",
                "Document analyzer",
                (
                    "Extract and correct the references from one paper, thesis or "
                    "bibliography, then export them."
                ),
                "",
            ),
            (
                "layers",
                "Batch processing",
                (
                    "Run a whole reading list at once and export a single merged "
                    "bibliography for your reference manager."
                ),
                "",
            ),
            (
                "search",
                "DOI lookup",
                (
                    "Resolve an identifier against CrossRef for publisher-supplied "
                    "metadata at full confidence."
                ),
                "",
            ),
        ]
    )

    st.write("")
    analyze_col, batch_col, doi_col = st.columns(3)
    with analyze_col:
        st.page_link(page("extract"), label="Open the analyzer")
    with batch_col:
        st.page_link(page("batch"), label="Open batch processing")
    with doi_col:
        st.page_link(page("doi"), label="Open DOI lookup")

    section_header(
        "What happens to your document",
        f"Accepted formats: {' · '.join(accepted_formats())}",
    )
    definition_list(list(_BEHAVIOURS))

    section_header("How results are reported")
    definition_list(list(_PRINCIPLES))


__all__ = ["render"]
