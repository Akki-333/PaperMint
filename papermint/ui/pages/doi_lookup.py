"""The DOI lookup page.

A single identifier is resolved against CrossRef and rendered as a citation
card identical to the ones produced by document parsing, so a looked-up
reference and an extracted one are directly comparable.

The result is held in session state, which means the card stays on screen
while the reader changes the export format instead of disappearing on the
next rerun.
"""

from __future__ import annotations

import logging

import streamlit as st

from papermint.enrichment.crossref import lookup_doi, normalize_doi
from papermint.errors import PaperMintError
from papermint.models import Citation
from papermint.ui.components.citation_card import render_citation_card
from papermint.ui.components.export_panel import render_export_panel, safe_filename
from papermint.ui.components.primitives import (
    definition_list,
    empty_state,
    notice,
    page_header,
    section_header,
)

logger = logging.getLogger(__name__)

_QUERY_KEY = "pm_doi_query"
_RESULT_KEY = "pm_doi_result"

#: Well-known identifiers offered as one-click examples.
_EXAMPLES: tuple[tuple[str, str], ...] = (
    ("10.1038/s41586-020-2649-2", "Array programming with NumPy, Nature"),
    ("10.1145/3292500.3330919", "Knowledge graph embedding, ACM"),
    ("10.1371/journal.pone.0173664", "Open access citation advantage, PLOS ONE"),
)


def _resolve(identifier: str) -> Citation | None:
    """Look up a DOI and report any failure in the page.

    Args:
        identifier: The DOI as typed by the reader.

    Returns:
        The citation, or None when the lookup produced nothing.
    """
    try:
        with st.spinner("Querying CrossRef…"):
            return lookup_doi(identifier)
    except PaperMintError as err:
        notice(
            "CrossRef could not be reached",
            str(err),
            tone="critical",
            details=[err.remedy] if err.remedy else None,
        )
    except Exception:
        logger.exception("Unexpected failure looking up %s", identifier)
        notice(
            "Something went wrong",
            "An unexpected error interrupted the lookup. The details were written "
            "to the application log.",
            tone="critical",
        )
    return None


def _render_examples() -> None:
    """Render the example identifiers as buttons that fill the field."""
    section_header("Try an example")
    for index, (identifier, description) in enumerate(_EXAMPLES):
        label_col, action_col = st.columns([5, 1])
        label_col.caption(f"**{description}** · {identifier}")
        if action_col.button("Use", key=f"pm_doi_example_{index}"):
            st.session_state[_QUERY_KEY] = identifier
            st.session_state.pop(_RESULT_KEY, None)
            st.rerun()


def _render_result(citation: Citation) -> None:
    """Render a resolved citation with its metadata and export panel.

    Args:
        citation: The citation returned by CrossRef.
    """
    notice(
        "Metadata retrieved",
        "CrossRef is the authoritative registry for this identifier, so every "
        "field below is publisher-supplied rather than parsed.",
        tone="positive",
    )
    st.write("")
    render_citation_card(citation, 1)

    section_header("Record")
    definition_list(
        [
            ("Title", citation.title),
            ("Authors", citation.author_string),
            ("Year", citation.year),
            ("Journal", citation.journal),
            ("Volume and pages", citation.locator),
            ("Publisher", citation.publisher),
            ("Type", citation.entry_type.label),
            ("DOI", citation.doi),
        ]
    )

    with st.expander("Raw record"):
        st.json(citation.model_dump(mode="json"))

    st.divider()
    render_export_panel(
        [citation],
        key_prefix="doi",
        default_name=safe_filename(citation.cite_key, "doi_record"),
    )


def render() -> None:
    """Render the DOI lookup page."""
    page_header(
        "DOI lookup",
        "Resolve a Digital Object Identifier against CrossRef to obtain "
        "publisher-supplied metadata, then export it in any supported format.",
        eyebrow="Lookup",
        eyebrow_icon="search",
    )

    field, action = st.columns([5, 1])
    query = field.text_input(
        "DOI",
        key=_QUERY_KEY,
        placeholder="10.1038/s41586-020-2649-2",
        label_visibility="collapsed",
        help="A bare DOI, or a full https://doi.org/ address.",
    )
    submitted = action.button("Look up", use_container_width=True, type="primary")

    if submitted:
        identifier = normalize_doi(query)
        if not identifier:
            notice(
                "Enter a DOI first",
                "A DOI looks like 10.1038/s41586-020-2649-2.",
                tone="caution",
            )
            return
        st.session_state[_RESULT_KEY] = _resolve(identifier)
        if st.session_state[_RESULT_KEY] is None:
            notice(
                "No record for that identifier",
                f"CrossRef returned nothing for {identifier}. Check the DOI for a "
                "typo, or look for the work under a different identifier.",
                tone="caution",
            )
            return

    citation = st.session_state.get(_RESULT_KEY)
    if citation is not None:
        _render_result(citation)
        return

    if not query:
        empty_state(
            "Nothing looked up yet",
            "Paste an identifier above, or pick one of the examples below.",
            icon_name="search",
        )
        _render_examples()


__all__ = ["render"]
