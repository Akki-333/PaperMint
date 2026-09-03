"""Safe HTML rendering helpers for the Streamlit presentation layer.

Two problems are solved here, both of which produced visible corruption in the
previous interface.

**Markdown leaks.** ``st.markdown(html, unsafe_allow_html=True)`` still runs
the Markdown parser first, so any line indented by four spaces is turned into a
code block and the layout collapses into grey monospace. Components were
therefore forced to build HTML as unindented string concatenation, which is
unreadable. ``render`` uses ``st.html``, which bypasses Markdown entirely, so
component markup can be written and indented normally.

**Unescaped document text.** Titles, authors and summaries come from arbitrary
uploaded documents. A single ``<`` or ``&`` in a title silently ate the rest of
a card. Every interpolated value must pass through :func:`esc`.
"""

from __future__ import annotations

import html as _html
import re

import streamlit as st

#: Collapses the leading indentation that component templates use for
#: readability. Applied before rendering so the emitted markup stays compact.
_LINE_INDENT = re.compile(r"^[ \t]+", re.MULTILINE)

#: Whitespace between adjacent tags, removed so that inline-block elements do
#: not inherit stray word spacing.
_TAG_GAP = re.compile(r">\s+<")


def esc(value: object) -> str:
    """Escape a value for safe interpolation into HTML.

    Args:
        value: Any value; ``None`` becomes an empty string.

    Returns:
        The value as HTML-escaped text, with quotes escaped as well.
    """
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)


def attr(value: object) -> str:
    """Escape a value for use inside a double-quoted HTML attribute.

    Args:
        value: Any value; ``None`` becomes an empty string.

    Returns:
        The escaped attribute value.
    """
    return esc(value)


def compact(markup: str) -> str:
    """Strip template indentation and inter-tag whitespace from markup.

    Args:
        markup: The component's HTML, indented for readability.

    Returns:
        Markup safe to hand to a renderer, with no leading indentation.
    """
    stripped = _LINE_INDENT.sub("", markup.strip())
    return _TAG_GAP.sub("><", stripped)


def render(markup: str) -> None:
    """Render component markup into the page.

    Args:
        markup: The HTML to insert. It is compacted first so that indented
            templates can never be mistaken for a Markdown code block.
    """
    st.html(compact(markup))


def clamp(text: str, limit: int) -> str:
    """Trim text to a length, breaking on a word boundary.

    Args:
        text: The text to shorten.
        limit: Maximum number of characters.

    Returns:
        The text, ending in a single-character ellipsis when it was cut.
    """
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"


def dot_join(*parts: str) -> str:
    """Join non-empty fragments with a middle dot separator.

    Args:
        *parts: The fragments; empty ones are dropped.

    Returns:
        The joined string.
    """
    return " · ".join(p for p in parts if p)


__all__ = ["attr", "clamp", "compact", "dot_join", "esc", "render"]
