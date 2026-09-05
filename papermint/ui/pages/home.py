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
from papermint.ui.html import render as render_html
from papermint.ui.icons import icon

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
        "Several reference lists in one file",
        (
            "Collects every block it can find, whether that is a list per chapter, "
            "separate primary and secondary sources, or a further-reading list after "
            "the references. An appendix or index between them is left in the body."
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
        "A high-precision document intelligence platform engineered for academic "
        "literature extraction, reference management, and bibliographic data integrity.",
        eyebrow="Academic Citation Intelligence",
        eyebrow_icon="leaf",
    )

    render_html(
        '<div class="pm-overview-panel">'
        '<div class="pm-overview-title">Context & Core Purpose</div>'
        '<div class="pm-overview-text">'
        "Academic literature review is the bedrock of scientific discovery, yet "
        "scholars, students, and research institutions routinely lose countless hours "
        "wrestling with malformed citations, inconsistent reference formatting, and "
        "fragile PDF text extraction. Most automated citation tools either hallucinate "
        "plausible-looking authors or break down when confronted with real-world complexities "
        "like annotated bibliographies, multi-column layouts, split linebreaks, and historical catalog formats."
        "</div>"
        '<div class="pm-overview-text">'
        "PaperMint was built to solve this challenge with zero guesswork. Guided by the governing "
        "principle of <strong>Honesty Over Completeness</strong>, the platform repairs document "
        "artifacts upstream through automated Unicode ligature and line-split normalization, "
        "isolates bibliographic boundaries, deterministically extracts up to eight core metadata fields, "
        "and assigns calibrated confidence scores. When a field is ambiguous, it is left empty and "
        "marked missing rather than fabricated—giving you 100% confidence when exporting to Zotero, "
        "Mendeley, Overleaf, or EndNote."
        "</div>"
        '<div class="pm-overview-pillars">'
        '<div class="pm-pillar">'
        f'<span class="pm-pillar-icon">{icon("check", size=16, stroke=1.8)}</span>'
        "<div>"
        '<div class="pm-pillar-heading">Zero Guesswork & Validation</div>'
        '<div class="pm-pillar-desc">Every candidate field is validated before acceptance. No hallucinated names or fabricated metadata.</div>'
        "</div>"
        "</div>"
        '<div class="pm-pillar">'
        f'<span class="pm-pillar-icon">{icon("sparkle", size=16, stroke=1.8)}</span>'
        "<div>"
        '<div class="pm-pillar-heading">Upstream Text Normalization</div>'
        '<div class="pm-pillar-desc">Repairs soft hyphens, typographic ligatures, and split words before parsing even begins.</div>'
        "</div>"
        "</div>"
        '<div class="pm-pillar">'
        f'<span class="pm-pillar-icon">{icon("download", size=16, stroke=1.8)}</span>'
        "<div>"
        '<div class="pm-pillar-heading">Universal Interoperability</div>'
        '<div class="pm-pillar-desc">Instant export to BibTeX, RIS, CSV, Excel, Word, and PDF, with human-in-the-loop inline correction.</div>'
        "</div>"
        "</div>"
        "</div>"
        "</div>"
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
                "quote",
                "Style studio",
                (
                    "Set what you extracted in APA, MLA, IEEE or Chicago, and read "
                    "what each style asks for and why."
                ),
                "",
            ),
        ]
    )

    st.write("")
    analyze_col, batch_col, style_col = st.columns(3)
    with analyze_col:
        st.page_link(page("extract"), label="Open the analyzer")
    with batch_col:
        st.page_link(page("batch"), label="Open batch processing")
    with style_col:
        st.page_link(page("styles"), label="Open the style studio")

    section_header(
        "What happens to your document",
        f"Accepted formats: {' · '.join(accepted_formats())}",
    )
    definition_list(list(_BEHAVIOURS))

    section_header("How results are reported")
    definition_list(list(_PRINCIPLES))


__all__ = ["render"]
