"""PaperMint — Academic citation extraction tool.

This is the Streamlit entry point. Run with: streamlit run app.py
"""

import streamlit as st
from papermint.config import APP_NAME, APP_ICON, APP_TAGLINE
from papermint.ui.styles import inject_custom_css
from papermint.ui.pages import extract, batch, doi_lookup, about

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS
inject_custom_css()

# Define pages
page_extract = st.Page(extract.render, title="Extract Citations", icon="📄", default=True, url_path="extract")
page_batch = st.Page(batch.render, title="Batch Processing", icon="📁", url_path="batch")
page_doi = st.Page(doi_lookup.render, title="DOI Lookup", icon="🔍", url_path="doi-lookup")
page_about = st.Page(about.render, title="About", icon="ℹ️", url_path="about")

# Navigation
pg = st.navigation(
    {
        "Tools": [page_extract, page_batch, page_doi],
        "Info": [page_about],
    }
)

# Global sidebar branding
st.sidebar.markdown(f"### {APP_ICON} {APP_NAME}")
st.sidebar.caption(APP_TAGLINE)
st.sidebar.divider()

pg.run()