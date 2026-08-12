"""About page for the Streamlit UI."""

import streamlit as st

from papermint.config import APP_DESCRIPTION, APP_VERSION


def render() -> None:
    """Render the about page."""
    # Hero section
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-title">🌿 PaperMint</div>
        <div class="hero-subtitle">{APP_DESCRIPTION}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 32px;">
        <span class="style-badge" style="font-size: 0.9em; padding: 6px 16px;">v{APP_VERSION}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Features Grid
    st.markdown("### ✨ Features")

    st.markdown("""
    <div class="feature-grid">
        <div class="feature-item">
            <div class="feature-icon">📄</div>
            <div class="feature-name">Multi-Format Support</div>
            <div class="feature-desc">Extract citations from PDF, Word, PowerPoint, and image files with intelligent format detection.</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">🧠</div>
            <div class="feature-name">Smart Parsing</div>
            <div class="feature-desc">Automatically detect bibliography sections and split individual citations using heuristic analysis.</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">🎨</div>
            <div class="feature-name">Style Detection</div>
            <div class="feature-desc">Recognizes standard academic styles — APA, MLA, IEEE, and Chicago — with confidence scoring.</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">🔍</div>
            <div class="feature-name">DOI Enrichment</div>
            <div class="feature-desc">Fetch rich metadata from CrossRef using DOIs to fill in missing title, author, and journal info.</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">📥</div>
            <div class="feature-name">Versatile Exports</div>
            <div class="feature-desc">Download citations in BibTeX, RIS, CSV, Excel, Word, or PDF formats — ready for any workflow.</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">📊</div>
            <div class="feature-name">Document Summary</div>
            <div class="feature-desc">Get an AI-powered extractive summary of your document alongside the bibliography extraction.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Architecture
    st.markdown("### 🏗️ How It Works")
    st.markdown("PaperMint uses a robust multi-stage pipeline to process documents:")

    mermaid_code = """
    ```mermaid
    graph LR
        A["📤 Upload"] --> B["📄 Text Extraction"]
        B --> C["🔍 Bibliography Detection"]
        C --> D["✂️ Citation Splitting"]
        D --> E["🎨 Style Detection"]
        E --> F["🧠 Citation Parsing"]
        F --> G["📥 Export"]
    ```
    """
    st.markdown(mermaid_code)

    st.divider()

    # Technology Stack
    st.markdown("### 🛠️ Technology Stack")
    st.markdown("""
    <div class="tech-stack">
        <span class="tech-pill">🖥️ Streamlit</span>
        <span class="tech-pill">🧠 spaCy NLP</span>
        <span class="tech-pill">📄 PyMuPDF</span>
        <span class="tech-pill">✅ Pydantic</span>
        <span class="tech-pill">🐍 Python 3.11+</span>
        <span class="tech-pill">🔬 CrossRef API</span>
        <span class="tech-pill">📊 openpyxl</span>
        <span class="tech-pill">🧪 pytest</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Open Source
    st.markdown("### 🌐 Open Source")
    st.markdown("PaperMint is an open-source tool. Contributions, issues, and feature requests are welcome!")

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🔗 View on GitHub", "https://github.com/Akki-333/PaperMint", use_container_width=True)
    with col2:
        st.link_button("🐛 Report an Issue", "https://github.com/Akki-333/PaperMint/issues", use_container_width=True)
