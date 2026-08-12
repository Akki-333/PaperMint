"""About page for the Streamlit UI."""

import streamlit as st
from papermint.config import APP_NAME, APP_VERSION, APP_DESCRIPTION

def render() -> None:
    """Render the about page."""
    st.title("ℹ️ About PaperMint")
    
    st.markdown(f"**Version**: `{APP_VERSION}`")
    st.markdown(APP_DESCRIPTION)
    
    st.divider()
    
    st.markdown("### Features")
    st.markdown("""
    * 📄 **Multi-format Support**: Extract from PDF, Word, PPTX, and Images.
    * 🧠 **Smart Parsing**: Automatically detect bibliography sections and split citations.
    * 🎨 **Style Detection**: Recognizes standard styles like APA, MLA, IEEE, etc.
    * 🔍 **DOI Enrichment**: Automatically fetch rich metadata from Crossref.
    * 📥 **Versatile Exports**: Download citations in BibTeX, RIS, CSV, Excel, Word, or PDF formats.
    """)
    
    st.divider()
    
    st.markdown("### Architecture")
    st.markdown("PaperMint uses a robust pipeline to process documents seamlessly:")
    
    # Render architecture diagram with Mermaid
    mermaid_code = """
    ```mermaid
    graph LR
        A[Upload Document] --> B[Text Extraction]
        B --> C[Bibliography Detection]
        C --> D[Citation Splitting]
        D --> E[Style Detection]
        E --> F[Citation Parsing]
        F --> G[Export]
    ```
    """
    st.markdown(mermaid_code)
    
    st.divider()
    
    st.markdown("### Technology Stack")
    st.markdown("""
    - **Frontend**: Streamlit
    - **Parsing & NLP**: spaCy, regex, Custom Heuristics
    - **PDF Processing**: PyMuPDF / pdfplumber
    - **Data Validation**: Pydantic
    """)
    
    st.divider()
    
    st.markdown("### Open Source")
    st.markdown("PaperMint is an open-source tool. Contributions, issues, and feature requests are welcome!")
    st.markdown("[View on GitHub](https://github.com/Akki-333/Bibliography_extraction)")
