"""The citation browser: search, sort, filter and paginate a reference list.

Every screen that shows more than a handful of citations needs the same four
controls, and until now only the analyzer had them. The batch page rendered
each file's entire list inside an accordion, so opening a document with 163
references dropped 163 cards into the page at once and pushed everything below
it — including the export — hundreds of pixels down.

The controls are therefore a component rather than a page concern. One list
behaves the same wherever it appears, and a page that gains a new list gains
paging with it instead of rediscovering the need later.

Widget keys are namespaced by ``key_prefix`` so several browsers can coexist
in one script run: the batch page renders two, one for the selected document
and one for the merged library.
"""

from __future__ import annotations

import streamlit as st

from papermint.config import CITATIONS_PER_PAGE
from papermint.models import Citation
from papermint.ui.components.citation_card import render_citation_list
from papermint.ui.components.primitives import empty_state
from papermint.ui.state import restore_within

#: Every ordering the browser offers. The first is the default, and it is the
#: order the document itself used, which is the only one that is not an
#: interpretation.
SORT_OPTIONS: tuple[str, ...] = (
    "Document order",
    "Confidence, lowest first",
    "Confidence, highest first",
    "Year, newest first",
    "Year, oldest first",
    "Title, A to Z",
)


def browser_keys(key_prefix: str) -> tuple[str, ...]:
    """List the widget keys one browser owns.

    Pages pass these to :func:`papermint.ui.state.restore` and
    :func:`papermint.ui.state.retain` so a browser's search text, ordering and
    page number survive a move to another page and back.

    Args:
        key_prefix: The prefix given to :func:`render_citation_browser`.

    Returns:
        The widget keys, in no particular order.
    """
    return (
        f"{key_prefix}_search",
        f"{key_prefix}_sort",
        f"{key_prefix}_review",
        f"{key_prefix}_page",
    )


def _sorted_citations(citations: list[Citation], order: str) -> list[tuple[int, Citation]]:
    """Apply a sort order while preserving each entry's original position.

    Args:
        citations: The citations in document order.
        order: One of :data:`SORT_OPTIONS`.

    Returns:
        ``(original index, citation)`` pairs in display order.
    """
    indexed = list(enumerate(citations))
    if order == "Confidence, lowest first":
        return sorted(indexed, key=lambda pair: pair[1].confidence)
    if order == "Confidence, highest first":
        return sorted(indexed, key=lambda pair: pair[1].confidence, reverse=True)
    if order == "Year, newest first":
        return sorted(indexed, key=lambda pair: pair[1].year or "0000", reverse=True)
    if order == "Year, oldest first":
        return sorted(indexed, key=lambda pair: pair[1].year or "9999")
    if order == "Title, A to Z":
        return sorted(indexed, key=lambda pair: pair[1].display_title.lower())
    return indexed


def _matches(citation: Citation, query: str) -> bool:
    """Test a citation against a free-text query.

    The source filename is part of the haystack, so a merged library can be
    narrowed to one document by typing part of its name.

    Args:
        citation: The citation to test.
        query: The lowercase search string.

    Returns:
        True when any displayed field contains the query.
    """
    haystack = (
        f"{citation.display_title} {citation.author_string} {citation.year} "
        f"{citation.venue} {citation.doi} {citation.source_file}"
    ).lower()
    return query in haystack


def render_citation_browser(
    citations: list[Citation],
    *,
    scope: str,
    key_prefix: str,
    editable: bool = False,
    show_source: bool = False,
    empty_title: str = "No references to show",
    empty_body: str = "This document produced no bibliographic entries.",
) -> tuple[int, Citation] | None:
    """Render a searchable, sortable, paginated citation list.

    Args:
        citations: The citations in document order.
        scope: Namespace for the cards' own widget keys.
        key_prefix: Namespace for the browser's controls. See
            :func:`browser_keys`.
        editable: Show the inline editor on every card.
        show_source: Show each entry's source file, for merged listings.
        empty_title: Headline shown when there is nothing to browse.
        empty_body: Explanation shown when there is nothing to browse.

    Returns:
        An ``(index into citations, updated citation)`` pair when the reader
        saved an edit, otherwise None.
    """
    if not citations:
        empty_state(empty_title, empty_body)
        return None

    st.session_state.setdefault(f"{key_prefix}_sort", SORT_OPTIONS[0])

    search_col, sort_col, filter_col = st.columns([3, 2, 2])
    query = search_col.text_input(
        "Search",
        placeholder="Filter by title, author, year, venue or DOI",
        key=f"{key_prefix}_search",
        label_visibility="collapsed",
    )
    order = sort_col.selectbox(
        "Sort", SORT_OPTIONS, key=f"{key_prefix}_sort", label_visibility="collapsed"
    )
    review_only = filter_col.toggle(
        "Needs review", key=f"{key_prefix}_review", help="Show only incomplete entries."
    )

    rows = _sorted_citations(citations, order)
    if query:
        needle = query.lower()
        rows = [pair for pair in rows if _matches(pair[1], needle)]
    if review_only:
        rows = [pair for pair in rows if pair[1].needs_review]

    if not rows:
        empty_state(
            "Nothing matches those filters",
            "Clear the search box or turn off the review filter to see every entry.",
            icon_name="filter",
        )
        return None

    page_key = f"{key_prefix}_page"
    total_pages = max(1, -(-len(rows) // CITATIONS_PER_PAGE))
    page = 1
    if total_pages > 1:
        # Filtering can shrink the list under the reader's feet. A remembered
        # page beyond the new last one has to be pulled back into range before
        # the slider sees it, whether it came from this session or from the
        # shadow copy that survived a page switch.
        current = st.session_state.get(page_key)
        if isinstance(current, int) and current > total_pages:
            st.session_state[page_key] = total_pages
        restore_within(page_key, 1, total_pages)
        page = st.slider("Page", 1, total_pages, key=page_key, help=f"{len(rows)} entries")
    window = rows[(page - 1) * CITATIONS_PER_PAGE : page * CITATIONS_PER_PAGE]

    st.caption(
        f"Showing {len(window)} of {len(citations)} references"
        + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
    )

    edit = render_citation_list(
        [citation for _, citation in window],
        scope=scope,
        editable=editable,
        show_source=show_source,
        start_index=(page - 1) * CITATIONS_PER_PAGE + 1,
        uids=[str(position) for position, _ in window],
    )
    if edit is None:
        return None

    offset, updated = edit
    return window[offset][0], updated


__all__ = ["SORT_OPTIONS", "browser_keys", "render_citation_browser"]
