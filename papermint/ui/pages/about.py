"""The about page.

Explains what the tool does, how the pipeline is staged, and what it is built
on. The pipeline stages are read from :class:`~papermint.pipeline.PipelineStage`
so this page cannot describe a sequence the service no longer runs.

The previous version embedded a Mermaid diagram inside an indented triple
quoted string. Every line carried four spaces of indentation, so Markdown
rendered it as a literal code block rather than a diagram; that content is now
a real list.
"""

from __future__ import annotations

import streamlit as st

from papermint.config import APP_DESCRIPTION, APP_NAME, APP_REPO_URL, APP_VERSION
from papermint.formatters.reference_formatter import style_guides
from papermint.models import CitationStyle
from papermint.pipeline import PipelineStage, accepted_formats
from papermint.ui.components.primitives import (
    chip_row,
    definition_list,
    page_header,
    prose,
    section_header,
    tile_grid,
)

#: What each pipeline stage contributes, in execution order.
_STAGE_DETAIL: dict[PipelineStage, str] = {
    PipelineStage.EXTRACT: (
        "Decodes the file, then repairs the text: typographic ligatures are "
        "folded, words broken across a line are rejoined, and running headers "
        "and page numbers are removed."
    ),
    PipelineStage.CHARACTERIZE: (
        "Classifies the document and collects every reference block in it, by "
        "heading, by title page, or by scanning backwards for citation density. "
        "An appendix or index between two lists stays in the body."
    ),
    PipelineStage.PARSE: (
        "Segments the block into entries, detects the citation style, and "
        "extracts eight fields from each entry with validation on every one."
    ),
    PipelineStage.SUMMARIZE: (
        "Scores the narrative body by content-word frequency and position to "
        "produce an extractive summary, skipping the references."
    ),
}

#: The libraries the application is built on.
_STACK: tuple[tuple[str, str], ...] = (
    ("layers", "Streamlit"),
    ("check", "Pydantic v2"),
    ("document", "PyMuPDF"),
    ("book", "python-docx"),
    ("grid", "python-pptx"),
    ("quote", "spaCy"),
    ("hash", "pandas"),
    ("download", "ReportLab"),
)


def render() -> None:
    """Render the about page."""
    page_header(
        APP_NAME,
        APP_DESCRIPTION,
        eyebrow=f"Version {APP_VERSION}",
        eyebrow_icon="leaf",
    )

    section_header("What it does")
    tile_grid(
        [
            (
                "document",
                "Reads five formats",
                (
                    f"{' · '.join(accepted_formats())}, including scanned pages "
                    "through optical character recognition."
                ),
                "",
            ),
            (
                "search",
                "Finds every bibliography",
                (
                    "Matches references headings, recognises a bibliography title "
                    "page, and locates unheaded blocks by citation density. A file "
                    "with several reference lists yields all of them."
                ),
                "",
            ),
            (
                "quote",
                "Reads and writes four styles",
                (
                    "APA, MLA, IEEE and Chicago are recognised on the way in and "
                    "rendered on the way out, with each style explained below."
                ),
                "",
            ),
            (
                "check",
                "Validates every field",
                (
                    "A candidate that looks like a page range, an author list or a "
                    "publisher is rejected rather than shown as a title."
                ),
                "",
            ),
            (
                "edit",
                "Accepts corrections",
                (
                    "Any field can be edited inline before export, and the coverage "
                    "score updates to match."
                ),
                "",
            ),
            (
                "download",
                "Exports six formats",
                (
                    "BibTeX, RIS, CSV, Excel, Word and PDF, ready for Zotero, "
                    "Mendeley, EndNote or Overleaf."
                ),
                "",
            ),
        ]
    )

    section_header("How the pipeline runs")
    definition_list(
        [
            (f"{index}. {stage.label}", detail)
            for index, (stage, detail) in enumerate(_STAGE_DETAIL.items(), start=1)
        ]
    )

    section_header("Citation styles, explained")
    prose(
        "PaperMint recognises four styles when it reads a document and can set your "
        "references in any of them afterwards, on the Style studio page. A style is "
        "not an arbitrary set of rules: each one is arranged around what its "
        "discipline needs to see first, and knowing that makes the rules easy to "
        "remember. MLA opens expanded because its structure differs most from the "
        "others."
    )
    for guide in style_guides():
        with st.expander(
            f"{guide.short_name} for {guide.disciplines.lower()}",
            expanded=guide.style is CitationStyle.MLA,
        ):
            prose(guide.principle)
            st.write("")
            definition_list(
                [
                    ("Full name", guide.name),
                    ("Reference list", guide.list_heading),
                    ("Ordering", guide.ordering),
                    ("Citing in text", guide.in_text),
                    ("A finished entry", guide.sample),
                ]
            )
            st.caption("The elements of an entry, in order, with the punctuation that closes each")
            definition_list(
                [(f"{n}. {name}", rule) for n, (name, rule) in enumerate(guide.elements, start=1)]
            )
            st.caption("What sets it apart")
            definition_list(
                [(f"Detail {n}", detail) for n, detail in enumerate(guide.distinctives, start=1)]
            )

    section_header("Built with")
    chip_row(list(_STACK))

    section_header("Design commitments")
    definition_list(
        [
            (
                "Zero fabricated data",
                "A document with no bibliography produces no citations at all.",
            ),
            (
                "Deterministic extraction",
                (
                    "Field parsing uses validated patterns, not general-purpose named "
                    "entity recognition, which reports place names and common nouns as "
                    "human authors."
                ),
            ),
            (
                "Framework-independent core",
                (
                    "Extraction, parsing, enrichment and export import nothing from "
                    "Streamlit, so the same engine runs headless from a command line."
                ),
            ),
        ]
    )

    st.divider()
    repo_col, issues_col = st.columns(2)
    with repo_col:
        st.link_button("View the source", APP_REPO_URL, use_container_width=True)
    with issues_col:
        st.link_button("Report an issue", f"{APP_REPO_URL}/issues", use_container_width=True)


__all__ = ["render"]
