"""CSS styling definitions for the PaperMint UI."""

import streamlit as st


def inject_custom_css() -> None:
    """Inject custom CSS into the Streamlit app using st.markdown."""
    css = """
    <style>
    /* Citation Card */
    .citation-card {
        border-left: 4px solid #34D399; /* Mint green accent */
        background-color: #1E293B;      /* Subtle dark background */
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        color: #F8FAFC;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .citation-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .citation-title {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 8px;
    }
    
    /* Confidence Bar */
    .confidence-container {
        width: 100%;
        background-color: #334155;
        border-radius: 4px;
        height: 8px;
        margin-top: 12px;
        overflow: hidden;
    }
    
    .confidence-bar {
        height: 100%;
        background-color: #34D399; /* Mint green fill */
        transition: width 0.5s ease-in-out;
    }
    
    /* Style Badge */
    .style-badge {
        display: inline-block;
        background-color: #34D399;
        color: #0F172A;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    /* Metric Card */
    .metric-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #334155;
    }
    
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #34D399;
    }
    
    .metric-label {
        color: #94A3B8;
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Export Section */
    .export-section {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 24px;
        margin-top: 32px;
        border: 1px dashed #475569;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
