"""Route definitions for the PaperMint application.

The page objects are built here rather than inside ``app.py`` so that any page
can link to any other page. Streamlit's ``st.page_link`` needs the page object
itself when pages are declared from callables, and a page module cannot reach
into the entry point script to find it.

Pages are cached for the lifetime of the process because ``st.Page`` objects
are cheap, immutable descriptors.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

#: Cache of built page objects, keyed by route name.
_PAGES: dict[str, Any] = {}

#: The route table: name, title, icon, url path and section.
_ROUTES: tuple[tuple[str, str, str, str, str], ...] = (
    ("home", "Dashboard", ":material/home:", "home", "Overview"),
    ("extract", "Document analyzer", ":material/description:", "analyze", "Workspace"),
    ("batch", "Batch processing", ":material/layers:", "batch", "Workspace"),
    ("styles", "Style studio", ":material/format_quote:", "style-studio", "Tools"),
    ("about", "About", ":material/info:", "about", "Help"),
)


def _renderer(name: str) -> Any:
    """Import a page module's render function on demand.

    Args:
        name: The route name.

    Returns:
        The module-level ``render`` callable for that route.
    """
    from papermint.ui.pages import about, batch, extract, home, style_studio

    return {
        "home": home.render,
        "extract": extract.render,
        "batch": batch.render,
        "styles": style_studio.render,
        "about": about.render,
    }[name]


def build_pages() -> dict[str, Any]:
    """Build, cache and return every page object by route name.

    Returns:
        A mapping of route name to ``st.Page``.
    """
    if _PAGES:
        return _PAGES

    for name, title, icon, url_path, _section in _ROUTES:
        _PAGES[name] = st.Page(
            _renderer(name),
            title=title,
            icon=icon,
            url_path=url_path,
            default=(name == "home"),
        )
    return _PAGES


def page(name: str) -> Any:
    """Return one page object by route name.

    Args:
        name: The route name, such as ``"extract"``.

    Returns:
        The corresponding ``st.Page``.
    """
    return build_pages()[name]


def route_names() -> list[str]:
    """List every route name in navigation order.

    Returns:
        The route names.
    """
    return [name for name, *_ in _ROUTES]


def build_navigation(only: str | None = None) -> Any:
    """Build the sidebar navigation, grouped by section.

    Args:
        only: Restrict the navigation to a single route. Used by the test
            suite to drive one page at a time, since a page object can only be
            run through a navigation.

    Returns:
        The navigation object to run.
    """
    pages = build_pages()

    if only is not None:
        return st.navigation([pages[only]])

    sections: dict[str, list[Any]] = {}
    for name, _title, _icon, _url, section in _ROUTES:
        sections.setdefault(section, []).append(pages[name])
    return st.navigation(sections)


__all__ = ["build_navigation", "build_pages", "page", "route_names"]
