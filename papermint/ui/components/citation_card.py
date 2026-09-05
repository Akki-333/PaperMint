"""The citation card: the atomic unit of the PaperMint interface.

A card shows what was parsed and, just as importantly, how much of it was
parsed. Confidence is expressed three ways at three levels of detail: a
coloured rule down the left edge that is readable at a glance, a band label in
the header, and an explicit list of missing fields on entries that need
attention. Nothing is ever labelled "Untitled"; an entry whose title could not
be isolated shows its own opening text instead.

Cards render as static markup by default. When ``editable`` is set the card is
wrapped in a keyed Streamlit container so that real widgets, an inline editor
and a BibTeX copy view, can live inside the card's chrome.
"""

from __future__ import annotations

import streamlit as st

from papermint.exporters.bibtex_exporter import export_bibtex
from papermint.models import Author, Citation, CitationStyle
from papermint.parsers.citation_parser import score_citation
from papermint.ui.html import clamp, dot_join, esc, render
from papermint.ui.icons import icon
from papermint.ui.theme import band_color, band_fill


def citation_preview_text(citation: Citation) -> str:
    """Return the one-line summary used in compact listings.

    Args:
        citation: The citation to describe.

    Returns:
        A short human-readable descriptor.
    """
    return dot_join(
        clamp(citation.display_title, 70),
        citation.short_author_string,
        citation.year,
    )


#: How many cards into a list the entrance cascade keeps growing. Past this the
#: delay is held constant, so paging to entry 80 does not mean waiting four
#: seconds for the last card to arrive.
_MAX_REVEAL_STEP = 10

#: The value shown where part of a reference's identity could not be read.
_ABSENT = '<span class="pm-field-absent">Not found</span>'


def _field(label: str, value: str, *, value_class: str = "") -> str:
    """Render one aligned label-and-value row.

    Args:
        label: The field name, shown in the left column.
        value: The value, already escaped or already markup.
        value_class: Extra classes for the value cell.

    Returns:
        The row's HTML.
    """
    classes = f"pm-field-val {value_class}".strip()
    return (
        '<div class="pm-field">'
        f'<dt class="pm-field-key">{esc(label)}</dt>'
        f'<dd class="{classes}">{value}</dd>'
        "</div>"
    )


def _venue_row(citation: Citation) -> tuple[str, str] | None:
    """Return the label and value for the entry's venue.

    The label follows what was actually parsed, so a chapter says "In" and a
    monograph says "Publisher" rather than all three being flattened into one
    ambiguous "Journal".

    Args:
        citation: The citation being rendered.

    Returns:
        A ``(label, value)`` pair, or None when no venue was found.
    """
    if citation.journal:
        return "Journal", citation.journal
    if citation.booktitle:
        return "In", citation.booktitle
    if citation.publisher:
        return "Publisher", citation.publisher
    return None


def _field_rows(citation: Citation, *, show_source: bool = False) -> str:
    """Build the aligned field grid for one citation.

    Title, authors and year always occupy a row, found or not: they are the
    identity of a reference, and a card that quietly dropped an absent one
    would leave the reader to notice the gap for themselves. Everything else
    appears only when there is something to show.

    Args:
        citation: The citation being rendered.
        show_source: Add a provenance row naming the file the entry came from.
            A merged batch library needs it; a single document does not.

    Returns:
        The grid's HTML.
    """
    title_class = "is-title" if citation.is_parsed else "is-title is-unparsed"
    rows = [
        _field("Title", esc(citation.display_title), value_class=title_class),
        _field("Authors", esc(citation.author_string) or _ABSENT),
        _field("Year", esc(citation.year) or _ABSENT, value_class="is-mono"),
    ]

    venue = _venue_row(citation)
    if venue is not None:
        rows.append(_field(venue[0], f"<em>{esc(venue[1])}</em>"))
        if citation.publisher and venue[0] != "Publisher":
            rows.append(_field("Publisher", esc(citation.publisher)))
    if citation.volume:
        rows.append(_field("Volume", esc(citation.volume), value_class="is-mono"))
    if citation.issue:
        rows.append(_field("Issue", esc(citation.issue), value_class="is-mono"))
    if citation.pages:
        rows.append(_field("Pages", esc(citation.pages), value_class="is-mono"))

    if citation.doi_url:
        label = citation.doi or citation.url
        link = (
            f'<a class="pm-card-link" href="{esc(citation.doi_url)}" '
            'target="_blank" rel="noopener noreferrer">'
            f"{esc(clamp(label, 64))}{icon('external', size=12)}</a>"
        )
        rows.append(_field("DOI" if citation.doi else "Link", link))

    rows.append(_field("Type", esc(citation.entry_type.label)))
    if show_source and citation.source_file:
        rows.append(_field("Source", esc(citation.source_file), value_class="is-mono is-source"))
    return f'<dl class="pm-fields">{"".join(rows)}</dl>'


def _card_markup(
    citation: Citation, index: int, *, reveal: int = 0, show_source: bool = False
) -> str:
    """Build the static markup for one citation.

    Args:
        citation: The citation to render.
        index: The 1-based position shown in the gutter.
        reveal: This card's place in the entrance cascade.
        show_source: Add the provenance row. See :func:`_field_rows`.

    Returns:
        The card's HTML.
    """
    band = citation.confidence_band
    colour = band_color(band)
    fill = band_fill(band)

    badges: list[str] = []
    if citation.style is not CitationStyle.UNKNOWN:
        badges.append(f'<span class="pm-chip is-mono">{esc(citation.style.label)}</span>')
    if citation.edited:
        badges.append('<span class="pm-chip is-accent">Edited</span>')
    badges.append(
        f'<span class="pm-band"><span class="pm-band-dot"></span>'
        f"{esc(band.label)} {citation.confidence:.0%}</span>"
    )

    missing_html = ""
    if citation.needs_review and citation.missing_fields:
        missing_html = (
            f'<div class="pm-missing">{icon("alert", size=12)} '
            f"Not found: {esc(', '.join(citation.missing_fields))}</div>"
        )

    step = min(max(reveal, 0), _MAX_REVEAL_STEP)
    return (
        f'<div class="pm-card" style="--pm-band:{colour};--pm-band-fill:{fill};'
        f'--pm-meter:{citation.confidence:.0%};--pm-step:{step};">'
        f'<div class="pm-card-index">{index:02d}</div>'
        "<div>"
        f'<div class="pm-card-head"><div class="pm-chip-row">{"".join(badges)}</div></div>'
        '<div class="pm-meter" role="presentation"><span class="pm-meter-fill"></span></div>'
        f"{_field_rows(citation, show_source=show_source)}{missing_html}"
        "</div>"
        "</div>"
    )


def _parse_author_field(value: str) -> list[Author]:
    """Convert an edited author string back into author models.

    Accepts semicolon-separated names in either ``Family, Given`` or
    ``Given Family`` order, which is how researchers actually type them.

    Args:
        value: The raw text from the editor field.

    Returns:
        The parsed authors.
    """
    authors: list[Author] = []
    for chunk in value.split(";"):
        name = chunk.strip().rstrip(",")
        if not name:
            continue
        if "," in name:
            family, _, given = name.partition(",")
            authors.append(Author(family=family.strip(), given=given.strip()))
        else:
            words = name.split()
            if len(words) == 1:
                authors.append(Author(family=words[0]))
            else:
                authors.append(Author(given=" ".join(words[:-1]), family=words[-1]))
    return authors


def _render_editor(citation: Citation, uid: str) -> Citation | None:
    """Render the inline field editor inside a popover.

    Args:
        citation: The citation being corrected.
        uid: A unique suffix for the widget keys.

    Returns:
        The updated citation when the reader saves, otherwise None.
    """
    with st.form(key=f"pmform-{uid}", border=False):
        title = st.text_input("Title", value=citation.title, key=f"pmt-{uid}")
        authors = st.text_input(
            "Authors",
            value="; ".join(a.citation_name for a in citation.authors),
            help=("Separate authors with a semicolon, for example: Smith, J. A.; Doe, R. B."),
            key=f"pma-{uid}",
        )
        col_year, col_vol, col_pages = st.columns(3)
        year = col_year.text_input("Year", value=citation.year, key=f"pmy-{uid}")
        volume = col_vol.text_input("Volume", value=citation.volume, key=f"pmv-{uid}")
        pages = col_pages.text_input("Pages", value=citation.pages, key=f"pmp-{uid}")
        journal = st.text_input("Journal or venue", value=citation.journal, key=f"pmj-{uid}")
        publisher = st.text_input("Publisher", value=citation.publisher, key=f"pmpub-{uid}")
        doi = st.text_input("DOI", value=citation.doi, key=f"pmd-{uid}")

        if not st.form_submit_button("Save changes", type="primary"):
            return None

    updated = citation.model_copy(
        update={
            "title": title.strip(),
            "authors": _parse_author_field(authors),
            "year": year.strip(),
            "volume": volume.strip(),
            "pages": pages.strip(),
            "journal": journal.strip(),
            "publisher": publisher.strip(),
            "doi": doi.strip(),
            "edited": True,
        }
    )
    updated.confidence = score_citation(updated)
    return updated


def render_citation_card(
    citation: Citation,
    index: int,
    *,
    scope: str = "main",
    editable: bool = False,
    uid: str | None = None,
    reveal: int = 0,
    show_source: bool = False,
) -> Citation | None:
    """Render a single citation as a card.

    Args:
        citation: The citation object to render.
        index: The 1-based index of the citation in the list.
        scope: Namespace for widget keys, so several lists can coexist on one
            page without key collisions.
        editable: Show the inline editor and BibTeX actions.
        uid: Stable identifier for widget keys; defaults to the index.
        reveal: This card's place in the entrance cascade.
        show_source: Name the file this entry came from. Set on merged
            listings, where entries from several documents sit side by side.

    Returns:
        The updated citation when the reader saved an edit, otherwise None.
    """
    if not editable:
        render(_card_markup(citation, index, reveal=reveal, show_source=show_source))
        return None

    key = f"{scope}-{uid if uid is not None else index}"
    result: Citation | None = None

    with st.container(key=f"pmcard-{key}"):
        render(_card_markup(citation, index, reveal=reveal, show_source=show_source))

        actions, spacer = st.columns([3, 5])
        with actions:
            edit_col, cite_col = st.columns(2)
            with edit_col.popover("Edit", use_container_width=True):
                result = _render_editor(citation, key)
            with cite_col.popover("BibTeX", use_container_width=True):
                st.caption("Use the copy button in the corner of the block.")
                st.code(export_bibtex([citation]), language="bibtex")
        spacer.empty()

    return result


def render_citation_list(
    citations: list[Citation],
    *,
    scope: str = "main",
    editable: bool = False,
    start_index: int = 1,
    uids: list[str] | None = None,
    show_source: bool = False,
) -> tuple[int, Citation] | None:
    """Render a list of citation cards.

    Args:
        citations: The citations to render, in display order.
        scope: Namespace for widget keys.
        editable: Show the inline editor on every card.
        start_index: The number shown on the first card.
        uids: Stable per-citation identifiers, used for widget keys. Defaults
            to the display position.
        show_source: Name each entry's source file. See
            :func:`render_citation_card`.

    Returns:
        A ``(list position, updated citation)`` pair when a card was edited,
        otherwise None.
    """
    edit: tuple[int, Citation] | None = None
    for offset, citation in enumerate(citations):
        uid = uids[offset] if uids and offset < len(uids) else str(offset)
        updated = render_citation_card(
            citation,
            start_index + offset,
            scope=scope,
            editable=editable,
            uid=uid,
            reveal=offset,
            show_source=show_source,
        )
        if updated is not None:
            edit = (offset, updated)
    return edit


__all__ = ["citation_preview_text", "render_citation_card", "render_citation_list"]
