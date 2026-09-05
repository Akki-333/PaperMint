"""Design tokens for the PaperMint interface.

One source of truth for colour, type, spacing and elevation, consumed both by
the stylesheet and by the Python that picks a colour for a confidence band.
Hard-coded hex values elsewhere in ``papermint/ui`` are a defect: the token
should be added here instead.

The palette follows the design blueprint: mint on deep slate, with the
surfaces layered so that a card, a panel and the page background are
distinguishable without any border at all.
"""

from __future__ import annotations

from typing import Final

from papermint.models import ConfidenceBand

# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------

#: Brand and semantic colours.
COLOR: Final[dict[str, str]] = {
    # Brand
    "accent": "#34D399",
    "accent-bright": "#6EE7B7",
    "accent-deep": "#10B981",
    "accent-ink": "#052E20",
    # Surfaces, from furthest back to closest to the reader.
    "canvas": "#0F172A",
    "surface": "#161F33",
    "surface-raised": "#1D293D",
    "surface-sunken": "#0B1120",
    # Lines
    "border": "#27354C",
    "border-strong": "#3A4B66",
    # Type
    "text": "#EEF2F8",
    "text-muted": "#9DACC2",
    "text-faint": "#6B7C96",
    # Status
    "positive": "#34D399",
    "caution": "#FBBF24",
    "critical": "#F87171",
    "info": "#60A5FA",
}

#: Translucent fills, used for chips and hover states.
ALPHA: Final[dict[str, str]] = {
    # A fully transparent accent, needed as the resting end of a pulsing ring:
    # animating to `transparent` fades through grey in some engines, animating
    # to the same hue at zero alpha does not.
    "accent-00": "rgba(52, 211, 153, 0)",
    "accent-08": "rgba(52, 211, 153, 0.08)",
    "accent-14": "rgba(52, 211, 153, 0.14)",
    "accent-24": "rgba(52, 211, 153, 0.24)",
    "caution-12": "rgba(251, 191, 36, 0.12)",
    "caution-28": "rgba(251, 191, 36, 0.28)",
    "critical-12": "rgba(248, 113, 113, 0.12)",
    "critical-28": "rgba(248, 113, 113, 0.28)",
    "info-12": "rgba(96, 165, 250, 0.12)",
    "shadow": "rgba(3, 7, 18, 0.45)",
}

#: Colour assigned to each confidence band.
BAND_COLOR: Final[dict[ConfidenceBand, str]] = {
    ConfidenceBand.HIGH: COLOR["positive"],
    ConfidenceBand.MEDIUM: COLOR["caution"],
    ConfidenceBand.LOW: COLOR["critical"],
}

#: Translucent fill matching each confidence band.
BAND_FILL: Final[dict[ConfidenceBand, str]] = {
    ConfidenceBand.HIGH: ALPHA["accent-14"],
    ConfidenceBand.MEDIUM: ALPHA["caution-12"],
    ConfidenceBand.LOW: ALPHA["critical-12"],
}


def band_color(band: ConfidenceBand) -> str:
    """Return the accent colour for a confidence band.

    Args:
        band: The confidence band.

    Returns:
        A hex colour string.
    """
    return BAND_COLOR.get(band, COLOR["text-faint"])


def band_fill(band: ConfidenceBand) -> str:
    """Return the translucent fill for a confidence band.

    Args:
        band: The confidence band.

    Returns:
        An ``rgba()`` colour string.
    """
    return BAND_FILL.get(band, ALPHA["info-12"])


# ---------------------------------------------------------------------------
# Type
# ---------------------------------------------------------------------------

#: Font stacks. A serif carries bibliographic content so that titles and
#: prose read as scholarly text rather than as interface chrome.
FONT: Final[dict[str, str]] = {
    "ui": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "text": "'Source Serif 4', 'Iowan Old Style', Georgia, serif",
    "mono": "'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, monospace",
}

#: Modular type scale, in rem against a 16px root.
TYPE_SCALE: Final[dict[str, str]] = {
    "micro": "0.6875rem",  # 11px — eyebrow labels
    "xs": "0.75rem",  # 12px — chips, captions
    "sm": "0.8125rem",  # 13px — metadata
    "base": "0.875rem",  # 14px — body
    "md": "1rem",  # 16px — lead paragraphs
    "lg": "1.125rem",  # 18px — card titles
    "xl": "1.375rem",  # 22px — section headings
    "2xl": "1.75rem",  # 28px — page titles
    "3xl": "2.25rem",  # 36px — hero
}

# ---------------------------------------------------------------------------
# Space, shape and motion
# ---------------------------------------------------------------------------

#: Spacing scale in pixels. Every margin and padding uses a step from here.
SPACE: Final[dict[str, str]] = {
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px",
    "16": "64px",
}

#: Corner radii.
RADIUS: Final[dict[str, str]] = {
    "sm": "6px",
    "md": "10px",
    "lg": "14px",
    "pill": "999px",
}

#: Two elevation levels only; more reads as noise on a dark ground.
SHADOW: Final[dict[str, str]] = {
    "raised": f"0 1px 2px {ALPHA['shadow']}",
    "floating": f"0 12px 32px -8px {ALPHA['shadow']}",
}

#: Shared easing and duration.
#:
#: ``fast`` and ``base`` are interface feedback: a hover, a focus ring, a
#: border warming up. ``enter`` and ``reveal`` are content arriving, and they
#: use a decelerating curve that overshoots nothing, so a list of citations
#: settles onto the page rather than sliding in like a carousel. ``stagger`` is
#: the delay step between neighbouring items in a revealed sequence: below
#: about 40ms the cascade reads as one flicker, above about 90ms the last item
#: feels late.
MOTION: Final[dict[str, str]] = {
    "fast": "120ms cubic-bezier(0.4, 0, 0.2, 1)",
    "base": "200ms cubic-bezier(0.4, 0, 0.2, 1)",
    "enter": "460ms cubic-bezier(0.16, 1, 0.3, 1)",
    "reveal": "620ms cubic-bezier(0.16, 1, 0.3, 1)",
    "stagger": "55ms",
}


def css_variables() -> str:
    """Render every token as a CSS custom property block.

    Returns:
        The contents of a ``:root { ... }`` declaration, without the selector.
    """
    lines: list[str] = []
    for name, value in COLOR.items():
        lines.append(f"--pm-color-{name}: {value};")
    for name, value in ALPHA.items():
        lines.append(f"--pm-fill-{name}: {value};")
    for name, value in FONT.items():
        lines.append(f"--pm-font-{name}: {value};")
    for name, value in TYPE_SCALE.items():
        lines.append(f"--pm-text-{name}: {value};")
    for name, value in SPACE.items():
        lines.append(f"--pm-space-{name}: {value};")
    for name, value in RADIUS.items():
        lines.append(f"--pm-radius-{name}: {value};")
    for name, value in SHADOW.items():
        lines.append(f"--pm-shadow-{name}: {value};")
    for name, value in MOTION.items():
        lines.append(f"--pm-motion-{name}: {value};")
    return "\n".join(f"    {line}" for line in lines)


__all__ = [
    "ALPHA",
    "BAND_COLOR",
    "BAND_FILL",
    "COLOR",
    "FONT",
    "MOTION",
    "RADIUS",
    "SHADOW",
    "SPACE",
    "TYPE_SCALE",
    "band_color",
    "band_fill",
    "css_variables",
]
