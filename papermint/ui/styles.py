"""CSS styling definitions for the PaperMint UI."""

import streamlit as st


def inject_custom_css() -> None:
    """Inject custom CSS into the Streamlit app using st.markdown."""
    css = """
    <style>
    /* ===== IMPORTS ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ===== GLOBAL ===== */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ===== CITATION CARD ===== */
    .citation-card {
        border-left: 3px solid #34D399;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9));
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        color: #F8FAFC;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .citation-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(52, 211, 153, 0.3), transparent);
    }

    .citation-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 40px rgba(52, 211, 153, 0.1);
        border-left-color: #6EE7B7;
    }

    .citation-title {
        font-weight: 600;
        font-size: 1.1em;
        margin-bottom: 8px;
        color: #F1F5F9;
        letter-spacing: -0.01em;
    }

    .citation-authors {
        color: #CBD5E1;
        margin-bottom: 6px;
        font-size: 0.95em;
    }

    .citation-meta {
        color: #94A3B8;
        font-size: 0.88em;
        font-style: italic;
    }

    .citation-doi {
        margin-top: 10px;
        font-size: 0.88em;
    }

    .citation-doi a {
        color: #60A5FA;
        text-decoration: none;
        transition: color 0.2s;
    }

    .citation-doi a:hover {
        color: #93C5FD;
        text-decoration: underline;
    }

    /* ===== CONFIDENCE BAR ===== */
    .conf-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 14px;
    }

    .conf-label {
        font-size: 0.78em;
        color: #64748B;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        white-space: nowrap;
        min-width: 72px;
    }

    .conf-track {
        flex: 1;
        background: rgba(51, 65, 85, 0.6);
        border-radius: 6px;
        height: 6px;
        overflow: hidden;
    }

    .conf-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .conf-fill-high {
        background: linear-gradient(90deg, #34D399, #6EE7B7);
    }

    .conf-fill-mid {
        background: linear-gradient(90deg, #FBBF24, #F59E0B);
    }

    .conf-fill-low {
        background: linear-gradient(90deg, #F87171, #EF4444);
    }

    .conf-pct {
        font-size: 0.78em;
        color: #94A3B8;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        min-width: 36px;
        text-align: right;
    }

    /* ===== STYLE BADGE ===== */
    .style-badge {
        display: inline-block;
        background: linear-gradient(135deg, #34D399, #10B981);
        color: #064E3B;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ===== METRIC CARD ===== */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.85));
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        border: 1px solid rgba(51, 65, 85, 0.5);
        backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        border-color: rgba(52, 211, 153, 0.3);
        box-shadow: 0 8px 32px rgba(52, 211, 153, 0.08);
    }

    .metric-value {
        font-size: 2.2em;
        font-weight: 700;
        background: linear-gradient(135deg, #34D399, #6EE7B7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }

    .metric-label {
        color: #94A3B8;
        font-size: 0.82em;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
        font-weight: 500;
    }

    /* ===== SUMMARY SECTION ===== */
    .summary-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.7));
        border-radius: 16px;
        padding: 28px 32px;
        border: 1px solid rgba(51, 65, 85, 0.4);
        position: relative;
    }

    .summary-container::before {
        content: '📝';
        font-size: 1.4em;
        position: absolute;
        top: 20px;
        right: 24px;
        opacity: 0.3;
    }

    .summary-heading {
        font-size: 1.15em;
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .summary-text {
        color: #CBD5E1;
        font-size: 1em;
        line-height: 1.75;
        letter-spacing: 0.01em;
    }

    .summary-meta {
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid rgba(51, 65, 85, 0.5);
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }

    .summary-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(52, 211, 153, 0.1);
        color: #6EE7B7;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82em;
        font-weight: 500;
    }

    /* ===== EXPORT SECTION ===== */
    .export-section {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.7));
        border-radius: 16px;
        padding: 28px;
        margin-top: 32px;
        border: 1px solid rgba(71, 85, 105, 0.4);
    }

    /* ===== RAW TEXT SECTION ===== */
    .raw-text-container {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(51, 65, 85, 0.4);
        border-radius: 12px;
        padding: 20px 24px;
        color: #CBD5E1;
        font-family: 'Inter', sans-serif;
        font-size: 0.92em;
        line-height: 1.7;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
    }

    .raw-text-container::-webkit-scrollbar {
        width: 6px;
    }

    .raw-text-container::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.4);
        border-radius: 3px;
    }

    .raw-text-container::-webkit-scrollbar-thumb {
        background: rgba(52, 211, 153, 0.3);
        border-radius: 3px;
    }

    .raw-text-stats {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }

    .raw-stat {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(51, 65, 85, 0.4);
        color: #94A3B8;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.82em;
        font-weight: 500;
    }

    /* ===== DOI LINK CARD ===== */
    .doi-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.85));
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(51, 65, 85, 0.5);
        margin-top: 16px;
    }

    /* ===== ABOUT PAGE ===== */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;
        margin-top: 16px;
    }

    .feature-item {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.7));
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(51, 65, 85, 0.4);
        transition: all 0.3s ease;
    }

    .feature-item:hover {
        border-color: rgba(52, 211, 153, 0.3);
        transform: translateY(-2px);
    }

    .feature-icon {
        font-size: 1.6em;
        margin-bottom: 10px;
    }

    .feature-name {
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 6px;
    }

    .feature-desc {
        color: #94A3B8;
        font-size: 0.9em;
        line-height: 1.5;
    }

    /* ===== TECH STACK ===== */
    .tech-stack {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 12px;
    }

    .tech-pill {
        background: rgba(52, 211, 153, 0.1);
        color: #6EE7B7;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 500;
        border: 1px solid rgba(52, 211, 153, 0.2);
        transition: all 0.2s;
    }

    .tech-pill:hover {
        background: rgba(52, 211, 153, 0.2);
    }

    /* ===== HERO SECTION ===== */
    .hero-section {
        text-align: center;
        padding: 40px 20px 30px;
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 2.4em;
        font-weight: 700;
        background: linear-gradient(135deg, #34D399, #6EE7B7, #A7F3D0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.1em;
        font-weight: 300;
    }

    /* ===== PIPELINE STEP ===== */
    .pipeline-header {
        font-size: 1em;
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 12px;
    }

    /* ===== BATCH FILE RESULT ===== */
    .batch-file-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
    }

    .batch-file-name {
        font-weight: 600;
        color: #E2E8F0;
    }

    .batch-file-count {
        background: rgba(52, 211, 153, 0.15);
        color: #6EE7B7;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82em;
        font-weight: 600;
    }

    /* ===== SIDEBAR BRANDING ===== */
    .sidebar-brand {
        text-align: center;
        padding: 16px 0;
    }

    .sidebar-brand-icon {
        font-size: 2.2em;
        margin-bottom: 4px;
    }

    .sidebar-brand-name {
        font-size: 1.4em;
        font-weight: 700;
        background: linear-gradient(135deg, #34D399, #6EE7B7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .sidebar-brand-tagline {
        color: #64748B;
        font-size: 0.82em;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 2px;
    }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
