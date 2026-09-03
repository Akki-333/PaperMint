"""Inline SVG icons for the PaperMint interface.

Emoji were replaced with a single stroked icon set because emoji render
differently on every platform, cannot inherit the text colour, and give an
interface an assembled-from-parts look. These icons are 24x24 on a 1.6 stroke,
inherit ``currentColor``, and scale with the text they sit beside.
"""

from __future__ import annotations

from typing import Final

#: Path data for each icon, drawn on a 24x24 grid.
_PATHS: Final[dict[str, str]] = {
    "document": (
        '<path d="M14 3v4a1 1 0 0 0 1 1h4"/>'
        '<path d="M5 8v-3a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-3"/>'
        '<path d="M3 12h10"/><path d="M10 9l3 3-3 3"/>'
    ),
    "library": (
        '<path d="M3 5a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
        '<path d="M12 5a2 2 0 0 1 2-2h1a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2z"/>'
        '<path d="M18.5 4.2l1.9 0.5a1 1 0 0 1 .7 1.2l-3.4 13a1 1 0 0 1-1.2.7"/>'
    ),
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    "download": (
        '<path d="M12 4v11"/><path d="M8 11l4 4 4-4"/>'
        '<path d="M4 17v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1"/>'
    ),
    "check": '<path d="M4 12.5l5 5L20 6.5"/>',
    "alert": (
        '<path d="M12 8v5"/><path d="M12 17h.01"/>'
        '<path d="M10.3 3.9L2.5 17.4A2 2 0 0 0 4.2 20.4h15.6a2 2 0 0 0 1.7-3'
        'L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
    ),
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "link": (
        '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
        '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>'
    ),
    "edit": ('<path d="M4 20h4l10.5-10.5a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>'),
    "copy": (
        '<rect x="9" y="9" width="12" height="12" rx="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    ),
    "sparkle": (
        '<path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4z"/>'
        '<path d="M18.5 16l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "hash": (
        '<path d="M5 9h14"/><path d="M5 15h14"/><path d="M10 4L8 20"/><path d="M16 4l-2 16"/>'
    ),
    "quote": (
        '<path d="M9 7H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h2v1a3 3 0 0 1-3 3"/>'
        '<path d="M19 7h-4a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h2v1a3 3 0 0 1-3 3"/>'
    ),
    "filter": '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    "grid": (
        '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
    ),
    "leaf": (
        '<path d="M4 20c0-8 5-13 16-14 0 11-5 15-11 15a5 5 0 0 1-5-1z"/>'
        '<path d="M9 15c1.5-3 4-5.5 7-7"/>'
    ),
    "arrow-right": '<path d="M4 12h15"/><path d="M13 6l6 6-6 6"/>',
    "external": (
        '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/>'
        '<path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>'
    ),
    "book": (
        '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H19v18H6.5A2.5 2.5 0 0 0 4 22z"/>'
        '<path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H19"/>'
    ),
}


def icon(name: str, *, size: int = 16, stroke: float = 1.6, cls: str = "") -> str:
    """Render an inline SVG icon that inherits the surrounding text colour.

    Args:
        name: The icon key. An unknown name renders nothing rather than
            raising, so a typo never breaks a page.
        size: Edge length in pixels.
        stroke: Stroke width on the 24-unit grid.
        cls: Extra CSS classes to add alongside ``pm-icon``.

    Returns:
        SVG markup, or an empty string when the icon is unknown.
    """
    path = _PATHS.get(name)
    if path is None:
        return ""
    classes = f"pm-icon {cls}".strip()
    return (
        f'<svg class="{classes}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
        'focusable="false">'
        f"{path}</svg>"
    )


def available_icons() -> list[str]:
    """List every icon name in the set.

    Returns:
        The sorted icon names.
    """
    return sorted(_PATHS)


__all__ = ["available_icons", "icon"]
