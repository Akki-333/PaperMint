"""Presentational primitives shared by every PaperMint page.

These are the reusable pieces of the design system: page and section headers,
statistic tiles, chips, notices, empty states and definition lists. Pages
compose them instead of hand-writing HTML, which is what keeps spacing and
type consistent from one screen to the next.

Every function renders directly into the page and returns ``None``. Values
that originate in an uploaded document are escaped before interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from papermint.ui.html import esc, render
from papermint.ui.icons import icon
from papermint.ui.theme import ALPHA, COLOR

#: The visual tone a notice can take.
NoticeTone = Literal["neutral", "positive", "caution", "critical", "info"]

#: Border tint and background fill for each notice tone.
_TONE_STYLE: dict[str, tuple[str, str]] = {
    "neutral": (COLOR["border-strong"], COLOR["surface"]),
    "positive": (COLOR["positive"], ALPHA["accent-08"]),
    "caution": (COLOR["caution"], ALPHA["caution-12"]),
    "critical": (COLOR["critical"], ALPHA["critical-12"]),
    "info": (COLOR["info"], ALPHA["info-12"]),
}

#: Default icon for each notice tone.
_TONE_ICON: dict[str, str] = {
    "neutral": "info",
    "positive": "check",
    "caution": "alert",
    "critical": "alert",
    "info": "info",
}


@dataclass(frozen=True, slots=True)
class Stat:
    """One tile in a statistics row.

    Attributes:
        label: The short uppercase label above the value.
        value: The value itself, already formatted for display.
        note: Optional supporting line beneath the value.
        icon_name: Optional icon rendered beside the label.
        textual: Set for word values so they use the smaller type size.
    """

    label: str
    value: str
    note: str = ""
    icon_name: str = ""
    textual: bool = False


def page_header(title: str, lede: str = "", *, eyebrow: str = "", eyebrow_icon: str = "") -> None:
    """Render the heading block at the top of a page.

    Args:
        title: The page title.
        lede: An optional sentence explaining what the page does.
        eyebrow: An optional short label above the title.
        eyebrow_icon: Icon name shown beside the eyebrow.
    """
    parts = ['<div class="pm-page-head">']
    if eyebrow:
        parts.append(f'<div class="pm-eyebrow">{icon(eyebrow_icon, size=13)}{esc(eyebrow)}</div>')
    parts.append(f'<h1 class="pm-title">{esc(title)}</h1>')
    if lede:
        parts.append(f'<p class="pm-lede">{esc(lede)}</p>')
    parts.append("</div>")
    render("".join(parts))


def section_header(title: str, note: str = "") -> None:
    """Render a section heading with an optional right-aligned note.

    Args:
        title: The section title.
        note: Optional supporting text, right aligned.
    """
    note_html = f'<span class="pm-section-note">{esc(note)}</span>' if note else ""
    render(
        '<div class="pm-section-head">'
        f'<h2 class="pm-section-title">{esc(title)}</h2>'
        f"{note_html}"
        "</div>"
    )


def stat_row(stats: list[Stat]) -> None:
    """Render a responsive row of statistic tiles.

    Args:
        stats: The tiles to display, in order.
    """
    if not stats:
        return

    tiles: list[str] = []
    for stat in stats:
        glyph = icon(stat.icon_name, size=12) if stat.icon_name else ""
        value_class = "pm-stat-value is-text" if stat.textual else "pm-stat-value"
        note = f'<div class="pm-stat-note">{esc(stat.note)}</div>' if stat.note else ""
        tiles.append(
            '<div class="pm-stat">'
            f'<div class="pm-stat-label">{glyph}{esc(stat.label)}</div>'
            f'<div class="{value_class}">{esc(stat.value)}</div>'
            f"{note}"
            "</div>"
        )
    render(f'<div class="pm-stats">{"".join(tiles)}</div>')


def chip_row(chips: list[tuple[str, str]], *, accent_first: bool = False) -> None:
    """Render a row of small labelled chips.

    Args:
        chips: ``(icon_name, label)`` pairs; an empty icon name renders none.
        accent_first: Give the first chip the accent treatment.
    """
    if not chips:
        return

    rendered: list[str] = []
    for index, (icon_name, label) in enumerate(chips):
        classes = "pm-chip is-accent" if accent_first and index == 0 else "pm-chip"
        glyph = icon(icon_name, size=12) if icon_name else ""
        rendered.append(f'<span class="{classes}">{glyph}{esc(label)}</span>')
    render(f'<div class="pm-chip-row">{"".join(rendered)}</div>')


def notice(
    title: str,
    body: str = "",
    *,
    tone: NoticeTone = "neutral",
    icon_name: str = "",
    details: list[str] | None = None,
) -> None:
    """Render an explanatory notice.

    This replaces Streamlit's stock alerts wherever the interface needs to
    explain a decision the pipeline made, such as declining to invent
    citations for a document that has no bibliography.

    Args:
        title: The headline.
        body: A sentence or two of explanation.
        tone: The visual tone.
        icon_name: Overrides the tone's default icon.
        details: Optional bullet points listed beneath the body.
    """
    tint, fill = _TONE_STYLE.get(tone, _TONE_STYLE["neutral"])
    glyph = icon(icon_name or _TONE_ICON.get(tone, "info"), size=18)

    body_html = f'<div class="pm-notice-body">{esc(body)}</div>' if body else ""
    details_html = ""
    if details:
        items = "".join(f"<li>{esc(item)}</li>" for item in details)
        details_html = f'<ul class="pm-notice-list">{items}</ul>'

    render(
        f'<div class="pm-notice" style="--pm-notice-tint:{tint};--pm-notice-fill:{fill};">'
        f'<div class="pm-notice-icon">{glyph}</div>'
        "<div>"
        f'<div class="pm-notice-title">{esc(title)}</div>'
        f"{body_html}{details_html}"
        "</div>"
        "</div>"
    )


def empty_state(title: str, body: str = "", *, icon_name: str = "library") -> None:
    """Render a centred placeholder for a view with nothing to show.

    Args:
        title: The headline.
        body: A sentence explaining what would appear here.
        icon_name: The icon shown above the headline.
    """
    body_html = f'<div class="pm-empty-body">{esc(body)}</div>' if body else ""
    render(
        '<div class="pm-empty">'
        f"{icon(icon_name, size=28, stroke=1.3)}"
        f'<div class="pm-empty-title">{esc(title)}</div>'
        f"{body_html}"
        "</div>"
    )


def definition_list(rows: list[tuple[str, str]]) -> None:
    """Render aligned key and value rows.

    Args:
        rows: ``(key, value)`` pairs. Rows with an empty value are skipped.
    """
    visible = [(key, value) for key, value in rows if value]
    if not visible:
        return

    items = "".join(
        '<div class="pm-def">'
        f'<div class="pm-def-key">{esc(key)}</div>'
        f'<div class="pm-def-val">{esc(value)}</div>'
        "</div>"
        for key, value in visible
    )
    render(f'<div class="pm-defs">{items}</div>')


def prose(text: str) -> None:
    """Render a block of body prose in the reading serif.

    Args:
        text: The paragraph to display.
    """
    if not text.strip():
        return
    render(f'<div class="pm-prose">{esc(text)}</div>')


def source_block(text: str) -> None:
    """Render raw document text in a scrollable monospace panel.

    Args:
        text: The text to display verbatim.
    """
    render(f'<div class="pm-source">{esc(text)}</div>')


def tile_grid(tiles: list[tuple[str, str, str, str]]) -> None:
    """Render a responsive grid of descriptive tiles.

    Args:
        tiles: ``(icon_name, name, description, hint)`` tuples. An empty hint
            omits the call-to-action line.
    """
    if not tiles:
        return

    cards: list[str] = []
    for icon_name, name, description, hint in tiles:
        hint_html = ""
        if hint:
            hint_html = f'<div class="pm-tile-hint">{esc(hint)}{icon("arrow-right", size=13)}</div>'
        cards.append(
            '<div class="pm-tile">'
            f'<div class="pm-tile-icon">{icon(icon_name, size=20, stroke=1.8)}</div>'
            f'<div class="pm-tile-name">{esc(name)}</div>'
            f'<div class="pm-tile-desc">{esc(description)}</div>'
            f"{hint_html}"
            "</div>"
        )
    render(f'<div class="pm-grid">{"".join(cards)}</div>')


__all__ = [
    "NoticeTone",
    "Stat",
    "chip_row",
    "definition_list",
    "empty_state",
    "notice",
    "page_header",
    "prose",
    "section_header",
    "source_block",
    "stat_row",
    "tile_grid",
]
