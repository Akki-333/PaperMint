"""Home/Dashboard page for the Streamlit UI."""

import streamlit as st
from papermint.config import APP_NAME, APP_DESCRIPTION

def render() -> None:
    """Render the home dashboard page."""
    
    # Hero section with premium styling
    st.markdown(f"""
    <div style="text-align: center; padding: 60px 20px 40px; margin-bottom: 20px;">
        <div style="font-size: 3.5em; margin-bottom: 20px;">🌿</div>
        <div class="hero-title" style="font-size: 3.5em;">Welcome to {APP_NAME}</div>
        <div class="hero-subtitle" style="font-size: 1.2em; max-width: 600px; margin: 0 auto 30px;">
            Your intelligent assistant for extracting, parsing, and managing academic citations from any document format.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card" style="padding: 30px 20px;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">📄</div>
            <div style="font-size: 1.2em; font-weight: 600; color: #F1F5F9; margin-bottom: 8px;">Document Analyzer</div>
            <div style="color: #94A3B8; font-size: 0.9em; line-height: 1.5; margin-bottom: 20px;">
                Extract citations and generate an AI summary from a single PDF, Word, or Image file.
            </div>
            <div style="color: #34D399; font-weight: 600; font-size: 0.9em;">Use the sidebar →</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card" style="padding: 30px 20px;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">📁</div>
            <div style="font-size: 1.2em; font-weight: 600; color: #F1F5F9; margin-bottom: 8px;">Batch Processing</div>
            <div style="color: #94A3B8; font-size: 0.9em; line-height: 1.5; margin-bottom: 20px;">
                Process dozens of papers at once and export a unified master bibliography.
            </div>
            <div style="color: #34D399; font-weight: 600; font-size: 0.9em;">Use the sidebar →</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="metric-card" style="padding: 30px 20px;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">🔍</div>
            <div style="font-size: 1.2em; font-weight: 600; color: #F1F5F9; margin-bottom: 8px;">DOI Enrichment</div>
            <div style="color: #94A3B8; font-size: 0.9em; line-height: 1.5; margin-bottom: 20px;">
                Lookup a specific DOI to instantly fetch rich, accurate metadata from CrossRef.
            </div>
            <div style="color: #34D399; font-weight: 600; font-size: 0.9em;">Use the sidebar →</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # Document types
    st.markdown("### 📚 Supported Document Types")
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 12px; padding: 24px; color: #CBD5E1; margin-top: 16px;">
        <div style="margin-bottom: 16px;"><strong>PaperMint is optimized for:</strong></div>
        <ul style="line-height: 1.8; margin-bottom: 20px;">
            <li>✅ Research Papers & Journal Articles</li>
            <li>✅ Academic Textbooks</li>
            <li>✅ Thesis & Dissertation Documents</li>
            <li>✅ Documents with explicit "References" or "Bibliography" sections</li>
        </ul>
        <div style="color: #94A3B8; font-size: 0.9em; border-top: 1px solid rgba(51, 65, 85, 0.4); padding-top: 16px;">
            <em>Note: General documents, stories, or policy briefs (e.g. without references sections) will yield a Document Summary but will automatically skip citation extraction.</em>
        </div>
    </div>
    """, unsafe_allow_html=True)
