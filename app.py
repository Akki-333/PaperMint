"""PaperMint - academic citation extraction.

Streamlit entry point. Run with::

    streamlit run app.py

This script does four things and nothing else: configure the page, configure
logging, inject the stylesheet, and hand control to the router. Every screen
lives in ``papermint/ui/pages`` and every unit of work lives in the domain
layer beneath ``papermint/``.
"""

from __future__ import annotations

import logging
import os

import streamlit as st

from papermint.config import APP_ICON, APP_NAME, APP_TAGLINE, APP_VERSION
from papermint.ui.html import render
from papermint.ui.icons import icon
from papermint.ui.navigation import build_navigation
from papermint.ui.styles import inject_custom_css


def _configure_logging() -> None:
    """Configure application logging once per process.

    Without this the domain layer's ``logger.error`` and ``logger.exception``
    calls are discarded, which makes a production failure invisible. The level
    is read from ``PAPERMINT_LOG_LEVEL`` and defaults to INFO.
    """
    if logging.getLogger("papermint").handlers:
        return

    level = os.getenv("PAPERMINT_LOG_LEVEL", "INFO").upper()
    resolved = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("papermint").setLevel(resolved)


def _render_sidebar_brand() -> None:
    """Render the wordmark and tagline at the top of the sidebar."""
    with st.sidebar:
        render(
            '<div class="pm-brand">'
            '<div class="pm-brand-row">'
            f'<span class="pm-brand-mark">{icon("leaf", size=18)}</span>'
            f'<span class="pm-brand-name">{APP_NAME}</span>'
            "</div>"
            f'<div class="pm-brand-tag">{APP_TAGLINE}</div>'
            "</div>"
        )


def main() -> None:
    """Configure the app and run the router."""
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": f"{APP_NAME} {APP_VERSION} - academic citation extraction.",
        },
    )

    _configure_logging()
    inject_custom_css()
    _render_sidebar_brand()

    navigation = build_navigation()
    st.sidebar.divider()
    st.sidebar.caption(f"Version {APP_VERSION}")
    navigation.run()


main()
