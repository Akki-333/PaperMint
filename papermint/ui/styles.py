"""The PaperMint stylesheet.

Everything here is derived from :mod:`papermint.ui.theme`. The sheet has three
parts:

1. **Foundations** - font faces, the token block, and base typography.
2. **Streamlit chrome** - overrides for the framework's own widgets so that
   tabs, buttons, inputs and the upload dropzone belong to the same design
   system as the custom components.
3. **Components** - the classes used by ``papermint/ui/components``.

Design decisions worth keeping: bibliographic content is set in a serif so it
reads as scholarship rather than interface chrome; gradient text appears
nowhere, because it flattens hierarchy when applied to every heading; and
elevation is limited to two levels so that depth still means something.
"""

from __future__ import annotations

import streamlit as st

from papermint.ui.theme import css_variables

_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2"
    "?family=Inter:wght@400;500;600;700"
    "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400"
    "&family=JetBrains+Mono:wght@400;500&display=swap');"
)


def _foundations() -> str:
    """Return font faces, design tokens and base typography.

    Returns:
        A CSS fragment.
    """
    return f"""
{_FONT_IMPORT}

:root {{
{css_variables()}
    --pm-max-width: 1180px;
}}

html, body, .stApp {{
    font-family: var(--pm-font-ui);
    color: var(--pm-color-text);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

.stApp {{
    background:
        radial-gradient(900px 420px at 12% -8%, rgba(52, 211, 153, 0.07), transparent 65%),
        var(--pm-color-canvas);
}}

.pm-icon {{
    flex: none;
    vertical-align: -0.18em;
}}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: var(--pm-color-border-strong);
    border: 3px solid transparent;
    border-radius: var(--pm-radius-pill);
    background-clip: content-box;
}}
::-webkit-scrollbar-thumb:hover {{ background-color: var(--pm-color-text-faint); }}
"""


def _chrome() -> str:
    """Return overrides for Streamlit's own widgets.

    Returns:
        A CSS fragment.
    """
    return """
[data-testid="stMainBlockContainer"] {
    max-width: var(--pm-max-width);
    padding: var(--pm-space-8) var(--pm-space-6) var(--pm-space-16);
}

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] {
    background: var(--pm-color-surface-sunken);
    border-right: 1px solid var(--pm-color-border);
}

hr, [data-testid="stDivider"] hr {
    border-color: var(--pm-color-border);
    margin: var(--pm-space-6) 0;
}

/* --- Tabs ------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: var(--pm-space-1);
    border-bottom: 1px solid var(--pm-color-border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: auto;
    padding: var(--pm-space-3) var(--pm-space-4);
    background: transparent;
    color: var(--pm-color-text-muted);
    font-size: var(--pm-text-base);
    font-weight: 500;
    letter-spacing: 0.01em;
    border-radius: var(--pm-radius-sm) var(--pm-radius-sm) 0 0;
    transition: color var(--pm-motion-fast), background var(--pm-motion-fast);
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--pm-color-text);
    background: var(--pm-fill-accent-08);
}
.stTabs [aria-selected="true"] { color: var(--pm-color-text); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--pm-color-accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* --- Buttons ---------------------------------------------------------- */
.stButton button, .stDownloadButton button, .stLinkButton a, .stPopover button {
    font-family: var(--pm-font-ui);
    font-size: var(--pm-text-base);
    font-weight: 500;
    border-radius: var(--pm-radius-sm);
    border: 1px solid var(--pm-color-border-strong);
    background: var(--pm-color-surface-raised);
    color: var(--pm-color-text);
    padding: var(--pm-space-2) var(--pm-space-4);
    transition: border-color var(--pm-motion-fast), background var(--pm-motion-fast),
                color var(--pm-motion-fast);
    box-shadow: none;
}
.stButton button:hover, .stDownloadButton button:hover,
.stLinkButton a:hover, .stPopover button:hover {
    border-color: var(--pm-color-accent);
    color: var(--pm-color-accent-bright);
    background: var(--pm-fill-accent-08);
}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
    background: var(--pm-color-accent);
    border-color: var(--pm-color-accent);
    color: var(--pm-color-accent-ink);
    font-weight: 600;
}
.stButton button[kind="primary"]:hover, .stDownloadButton button[kind="primary"]:hover {
    background: var(--pm-color-accent-bright);
    border-color: var(--pm-color-accent-bright);
    color: var(--pm-color-accent-ink);
}
.stButton button:focus-visible, .stDownloadButton button:focus-visible {
    outline: 2px solid var(--pm-color-accent);
    outline-offset: 2px;
}

/* --- Inputs ----------------------------------------------------------- */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: var(--pm-color-surface-sunken);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-sm);
    color: var(--pm-color-text);
    font-size: var(--pm-text-base);
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--pm-color-accent);
    box-shadow: 0 0 0 3px var(--pm-fill-accent-14);
}
[data-baseweb="select"] > div {
    background: var(--pm-color-surface-sunken);
    border-color: var(--pm-color-border);
    border-radius: var(--pm-radius-sm);
    font-size: var(--pm-text-base);
}
[data-baseweb="select"] > div:hover { border-color: var(--pm-color-border-strong); }

/* --- File uploader ---------------------------------------------------- */
[data-testid="stFileUploaderDropzone"] {
    background: var(--pm-color-surface);
    border: 1px dashed var(--pm-color-border-strong);
    border-radius: var(--pm-radius-lg);
    padding: var(--pm-space-6);
    transition: border-color var(--pm-motion-base), background var(--pm-motion-base);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--pm-color-accent);
    background: var(--pm-fill-accent-08);
}

/* --- Expanders -------------------------------------------------------- */
[data-testid="stExpander"] details {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-md);
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: var(--pm-text-base); font-weight: 500; }
[data-testid="stExpander"] summary:hover { color: var(--pm-color-accent-bright); }

/* --- Alerts ----------------------------------------------------------- */
[data-testid="stAlertContainer"] {
    border-radius: var(--pm-radius-md);
    border: 1px solid var(--pm-color-border);
    font-size: var(--pm-text-base);
}

/* --- Progress --------------------------------------------------------- */
.stProgress > div > div > div > div { background: var(--pm-color-accent); }
.stProgress > div > div > div { background: var(--pm-color-border); }
"""


def _components() -> str:
    """Return the styles for PaperMint's own components.

    Returns:
        A CSS fragment.
    """
    return """
/* --- Page header ------------------------------------------------------ */
.pm-page-head { margin-bottom: var(--pm-space-8); }
.pm-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: var(--pm-space-2);
    font-size: var(--pm-text-micro);
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--pm-color-accent);
    margin-bottom: var(--pm-space-3);
}
.pm-title {
    font-family: var(--pm-font-text);
    font-size: var(--pm-text-2xl);
    font-weight: 600;
    letter-spacing: -0.015em;
    line-height: 1.2;
    color: var(--pm-color-text);
    margin: 0;
}
.pm-lede {
    font-size: var(--pm-text-md);
    line-height: 1.6;
    color: var(--pm-color-text-muted);
    max-width: 62ch;
    margin-top: var(--pm-space-3);
}

.pm-section-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--pm-space-4);
    margin: var(--pm-space-8) 0 var(--pm-space-4);
}
.pm-section-title {
    font-size: var(--pm-text-xl);
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--pm-color-text);
}
.pm-section-note { font-size: var(--pm-text-sm); color: var(--pm-color-text-faint); }

/* --- Stat tiles ------------------------------------------------------- */
.pm-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: var(--pm-space-3);
}
.pm-stat {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-md);
    padding: var(--pm-space-4) var(--pm-space-5);
}
.pm-stat-label {
    display: flex;
    align-items: center;
    gap: var(--pm-space-2);
    font-size: var(--pm-text-micro);
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pm-color-text-faint);
}
.pm-stat-value {
    margin-top: var(--pm-space-2);
    font-size: var(--pm-text-2xl);
    font-weight: 600;
    line-height: 1.1;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    color: var(--pm-color-text);
}
.pm-stat-value.is-text { font-size: var(--pm-text-xl); }
.pm-stat-note {
    margin-top: var(--pm-space-1);
    font-size: var(--pm-text-xs);
    color: var(--pm-color-text-faint);
}

/* --- Chips ------------------------------------------------------------ */
.pm-chip-row { display: flex; flex-wrap: wrap; gap: var(--pm-space-2); }
.pm-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--pm-space-1);
    padding: 3px var(--pm-space-3);
    border-radius: var(--pm-radius-pill);
    border: 1px solid var(--pm-color-border);
    background: var(--pm-color-surface-raised);
    color: var(--pm-color-text-muted);
    font-size: var(--pm-text-xs);
    font-weight: 500;
    white-space: nowrap;
}
.pm-chip.is-accent {
    background: var(--pm-fill-accent-08);
    border-color: var(--pm-fill-accent-24);
    color: var(--pm-color-accent-bright);
}
.pm-chip.is-mono {
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-micro);
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* --- Citation card ---------------------------------------------------- */
.pm-card {
    position: relative;
    display: grid;
    grid-template-columns: 2.4rem 1fr;
    gap: var(--pm-space-4);
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-left: 2px solid var(--pm-band, var(--pm-color-border-strong));
    border-radius: var(--pm-radius-md);
    padding: var(--pm-space-5);
    transition: border-color var(--pm-motion-fast), background var(--pm-motion-fast);
    animation: pm-rise var(--pm-motion-enter) both;
    animation-delay: calc(var(--pm-step, 0) * var(--pm-motion-stagger));
}
.pm-card:hover {
    border-color: var(--pm-color-border-strong);
    border-left-color: var(--pm-band, var(--pm-color-border-strong));
    background: var(--pm-color-surface-raised);
}
.pm-card-index {
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-sm);
    font-variant-numeric: tabular-nums;
    color: var(--pm-color-text-faint);
    padding-top: 2px;
}
.pm-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    gap: var(--pm-space-4);
    margin-bottom: var(--pm-space-3);
}

/* The coverage meter: the same number the badge carries, read as a length
   rather than a percentage, so a page of cards can be scanned without being
   read. */
.pm-meter {
    height: 3px;
    margin-bottom: var(--pm-space-4);
    border-radius: var(--pm-radius-pill);
    background: var(--pm-color-surface-sunken);
    overflow: hidden;
}
.pm-meter-fill {
    display: block;
    height: 100%;
    width: var(--pm-meter, 0%);
    border-radius: inherit;
    background: var(--pm-band, var(--pm-color-border-strong));
    animation: pm-meter-grow var(--pm-motion-reveal) both;
    animation-delay: calc(var(--pm-step, 0) * var(--pm-motion-stagger));
}

/* Every field is labelled and every label column is the same width, so values
   line up down the page and a reader compares like with like. */
.pm-fields { display: grid; gap: var(--pm-space-2); margin: 0; }
.pm-field {
    display: grid;
    grid-template-columns: 84px 1fr;
    gap: var(--pm-space-4);
    align-items: baseline;
}
.pm-field-key {
    margin: 0;
    font-size: var(--pm-text-micro);
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--pm-color-text-faint);
}
.pm-field-val {
    margin: 0;
    min-width: 0;
    font-size: var(--pm-text-base);
    line-height: 1.5;
    color: var(--pm-color-text-muted);
    overflow-wrap: anywhere;
}
.pm-field-val.is-title {
    font-family: var(--pm-font-text);
    font-size: var(--pm-text-lg);
    font-weight: 600;
    line-height: 1.35;
    letter-spacing: -0.005em;
    color: var(--pm-color-text);
}
.pm-field-val.is-title.is-unparsed {
    font-family: var(--pm-font-ui);
    font-size: var(--pm-text-base);
    font-weight: 400;
    font-style: italic;
    color: var(--pm-color-text-muted);
}
.pm-field-val.is-mono {
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-sm);
    font-variant-numeric: tabular-nums;
}
.pm-field-val em {
    font-family: var(--pm-font-text);
    font-style: italic;
    color: var(--pm-color-text);
}
.pm-field-absent {
    font-size: var(--pm-text-sm);
    font-style: italic;
    color: var(--pm-color-text-faint);
}
.pm-card-link {
    display: inline-flex;
    align-items: center;
    gap: var(--pm-space-2);
    font-size: var(--pm-text-sm);
    font-family: var(--pm-font-mono);
    color: var(--pm-color-info);
    text-decoration: none;
    word-break: break-all;
}
.pm-card-link:hover { text-decoration: underline; }

.pm-band {
    display: inline-flex;
    align-items: center;
    gap: var(--pm-space-2);
    padding: 3px var(--pm-space-3);
    border-radius: var(--pm-radius-pill);
    font-size: var(--pm-text-micro);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
    background: var(--pm-band-fill);
    color: var(--pm-band);
    border: 1px solid var(--pm-band-fill);
}
.pm-band-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: currentColor;
}
.pm-missing {
    margin-top: var(--pm-space-3);
    font-size: var(--pm-text-xs);
    color: var(--pm-color-caution);
}

/* Interactive cards wrap real Streamlit widgets, so the chrome lives on
   the keyed container rather than on a markup-only element. */
[class*="st-key-pmcard-"] {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-md);
    padding: var(--pm-space-2) var(--pm-space-4) var(--pm-space-3);
    margin-bottom: var(--pm-space-3);
}
[class*="st-key-pmcard-"] .pm-card {
    background: transparent;
    border: none;
    border-left: 2px solid var(--pm-band, var(--pm-color-border-strong));
    padding: var(--pm-space-3) 0 var(--pm-space-3) var(--pm-space-4);
}
[class*="st-key-pmcard-"] .pm-card:hover { background: transparent; }
[class*="st-key-pmcard-"] .stButton button,
[class*="st-key-pmcard-"] .stPopover button {
    font-size: var(--pm-text-xs);
    padding: var(--pm-space-1) var(--pm-space-3);
}

/* --- Notice ----------------------------------------------------------- */
.pm-notice {
    display: flex;
    gap: var(--pm-space-4);
    padding: var(--pm-space-5);
    border-radius: var(--pm-radius-md);
    border: 1px solid var(--pm-notice-tint, var(--pm-color-border));
    background: var(--pm-notice-fill, var(--pm-color-surface));
}
.pm-notice-icon { color: var(--pm-notice-tint, var(--pm-color-text-muted)); padding-top: 2px; }
.pm-notice-title {
    font-size: var(--pm-text-base);
    font-weight: 600;
    color: var(--pm-color-text);
}
.pm-notice-body {
    margin-top: var(--pm-space-2);
    font-size: var(--pm-text-base);
    line-height: 1.6;
    color: var(--pm-color-text-muted);
    max-width: 72ch;
}
.pm-notice-list {
    margin: var(--pm-space-3) 0 0;
    padding-left: var(--pm-space-5);
    font-size: var(--pm-text-sm);
    line-height: 1.7;
    color: var(--pm-color-text-faint);
}

/* --- Processing flow -------------------------------------------------- */
/* The rail is a plain progress bar rather than a set of connectors drawn
   between the nodes: connectors have to be positioned against node centres,
   which drift with the label width, and a bar that is always exactly as long
   as the row cannot come apart. */
.pm-flow {
    padding: var(--pm-space-5);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-lg);
    background: var(--pm-color-surface);
}
.pm-flow.is-live { animation: pm-rise var(--pm-motion-enter) both; }

.pm-flow-rail {
    position: relative;
    height: 3px;
    margin-bottom: var(--pm-space-5);
    border-radius: var(--pm-radius-pill);
    background: var(--pm-color-surface-sunken);
    overflow: hidden;
}
.pm-flow-fill {
    display: block;
    height: 100%;
    width: var(--pm-to, 0%);
    border-radius: inherit;
    background: linear-gradient(
        90deg,
        var(--pm-color-accent-deep),
        var(--pm-color-accent-bright)
    );
}
/* Streamlit remounts the whole node on every placeholder write, so a
   transition would never play. The fill animates from where the previous
   stage left it, which the stepper remembers, to where this one reaches. */
.pm-flow.is-live .pm-flow-fill { animation: pm-flow-advance var(--pm-motion-reveal) both; }
.pm-flow.is-live .pm-flow-rail::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        var(--pm-fill-accent-00),
        var(--pm-fill-accent-24),
        var(--pm-fill-accent-00)
    );
    animation: pm-flow-sweep 1.7s linear infinite;
}

.pm-flow-steps {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--pm-space-2);
    margin: 0;
    padding: 0;
    list-style: none;
}
.pm-flow-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--pm-space-2);
    text-align: center;
}
.pm-flow.is-live .pm-flow-step {
    animation: pm-rise var(--pm-motion-enter) both;
    animation-delay: calc(var(--pm-step, 0) * var(--pm-motion-stagger));
}
.pm-flow-node {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 1px solid var(--pm-color-border);
    background: var(--pm-color-surface-sunken);
    color: var(--pm-color-text-faint);
    transition: color var(--pm-motion-base), border-color var(--pm-motion-base),
                background var(--pm-motion-base);
}
.pm-flow-name {
    font-size: var(--pm-text-xs);
    line-height: 1.35;
    color: var(--pm-color-text-faint);
}
.pm-flow-step.is-done .pm-flow-node {
    color: var(--pm-color-accent);
    border-color: var(--pm-fill-accent-24);
    background: var(--pm-fill-accent-08);
}
.pm-flow-step.is-done .pm-flow-name { color: var(--pm-color-text-muted); }
.pm-flow-step.is-active .pm-flow-node {
    color: var(--pm-color-accent-ink);
    border-color: var(--pm-color-accent);
    background: var(--pm-color-accent);
}
.pm-flow.is-live .pm-flow-step.is-active .pm-flow-node {
    animation: pm-flow-pulse 1.8s ease-out infinite;
}
.pm-flow-step.is-active .pm-flow-name {
    color: var(--pm-color-accent-bright);
    font-weight: 600;
}

.pm-flow-status {
    display: flex;
    align-items: flex-start;
    gap: var(--pm-space-3);
    margin-top: var(--pm-space-5);
    padding-top: var(--pm-space-4);
    border-top: 1px solid var(--pm-color-border);
    font-size: var(--pm-text-sm);
    line-height: 1.6;
    color: var(--pm-color-text-muted);
}
.pm-flow-said b { color: var(--pm-color-text); font-weight: 600; }
.pm-flow-beacon {
    flex: none;
    width: 8px;
    height: 8px;
    margin-top: 6px;
    border-radius: 50%;
    background: var(--pm-color-accent);
    animation: pm-flow-beacon 1.3s ease-in-out infinite;
}

/* --- Summary and source text ------------------------------------------ */
.pm-prose {
    font-family: var(--pm-font-text);
    font-size: 1.0625rem;
    line-height: 1.72;
    color: var(--pm-color-text);
    max-width: 68ch;
}

.pm-panel {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-lg);
    padding: var(--pm-space-6);
}

.pm-source {
    background: var(--pm-color-surface-sunken);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-md);
    padding: var(--pm-space-5);
    color: var(--pm-color-text-muted);
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-sm);
    line-height: 1.75;
    max-height: 460px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    tab-size: 2;
}

/* --- Quick actions and feature grid ----------------------------------- */
.pm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--pm-space-4);
}
.pm-tile {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-radius: var(--pm-radius-lg);
    padding: var(--pm-space-5);
    transition: border-color var(--pm-motion-fast);
}
.pm-tile:hover { border-color: var(--pm-color-border-strong); }
.pm-tile-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px; height: 38px;
    border-radius: var(--pm-radius-md);
    background: var(--pm-fill-accent-08);
    border: 1px solid var(--pm-fill-accent-24);
    color: var(--pm-color-accent);
    margin-bottom: var(--pm-space-4);
    box-shadow: 0 0 12px var(--pm-fill-accent-08);
}
.pm-tile-name {
    font-size: var(--pm-text-md);
    font-weight: 600;
    color: var(--pm-color-text);
}
.pm-tile-desc {
    margin-top: var(--pm-space-2);
    font-size: var(--pm-text-base);
    line-height: 1.6;
    color: var(--pm-color-text-muted);
}
.pm-tile-hint {
    margin-top: var(--pm-space-4);
    font-size: var(--pm-text-xs);
    font-weight: 500;
    color: var(--pm-color-accent);
    display: inline-flex;
    align-items: center;
    gap: var(--pm-space-2);
}

/* --- Overview narrative panel ---------------------------------------- */
.pm-overview-panel {
    background: var(--pm-color-surface);
    border: 1px solid var(--pm-color-border);
    border-left: 3px solid var(--pm-color-accent);
    border-radius: var(--pm-radius-lg);
    padding: var(--pm-space-6);
    margin-bottom: var(--pm-space-8);
}
.pm-overview-title {
    font-family: var(--pm-font-text);
    font-size: var(--pm-text-xl);
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--pm-color-text);
    margin: 0 0 var(--pm-space-3);
}
.pm-overview-text {
    font-family: var(--pm-font-ui);
    font-size: var(--pm-text-base);
    line-height: 1.72;
    color: var(--pm-color-text-muted);
    margin: 0 0 var(--pm-space-3);
}
.pm-overview-text:last-of-type {
    margin-bottom: 0;
}
.pm-overview-pillars {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: var(--pm-space-4);
    margin-top: var(--pm-space-5);
    padding-top: var(--pm-space-5);
    border-top: 1px solid var(--pm-color-border);
}
.pm-pillar {
    display: flex;
    gap: var(--pm-space-3);
    align-items: flex-start;
}
.pm-pillar-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: var(--pm-radius-sm);
    background: var(--pm-fill-accent-08);
    border: 1px solid var(--pm-fill-accent-24);
    color: var(--pm-color-accent);
    flex-shrink: 0;
    margin-top: 2px;
}
.pm-pillar-heading {
    font-size: var(--pm-text-sm);
    font-weight: 600;
    color: var(--pm-color-text);
    margin-bottom: var(--pm-space-1);
}
.pm-pillar-desc {
    font-size: var(--pm-text-xs);
    line-height: 1.55;
    color: var(--pm-color-text-muted);
}

/* --- Definition rows -------------------------------------------------- */
.pm-defs { display: grid; gap: var(--pm-space-3); }
.pm-def {
    display: grid;
    grid-template-columns: minmax(120px, 180px) 1fr;
    gap: var(--pm-space-4);
    padding-bottom: var(--pm-space-3);
    border-bottom: 1px solid var(--pm-color-border);
    font-size: var(--pm-text-base);
}
.pm-def:last-child { border-bottom: none; padding-bottom: 0; }
.pm-def-key { color: var(--pm-color-text-faint); }
.pm-def-val { color: var(--pm-color-text); }

/* --- Sidebar brand ---------------------------------------------------- */
.pm-brand { padding: var(--pm-space-3) 0 var(--pm-space-4); }
.pm-brand-row {
    display: flex;
    align-items: center;
    gap: var(--pm-space-3);
}
.pm-brand-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px; height: 36px;
    border-radius: var(--pm-radius-md);
    background: var(--pm-color-accent);
    color: var(--pm-color-accent-ink);
    box-shadow: 0 0 14px var(--pm-fill-accent-24);
}
.pm-brand-name {
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--pm-color-text);
}
.pm-brand-tag {
    margin-top: var(--pm-space-2);
    font-size: var(--pm-text-micro);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--pm-color-text-faint);
}

/* --- Empty state ------------------------------------------------------ */
.pm-empty {
    text-align: center;
    padding: var(--pm-space-12) var(--pm-space-6);
    border: 1px dashed var(--pm-color-border);
    border-radius: var(--pm-radius-lg);
    color: var(--pm-color-text-faint);
}
.pm-empty-title {
    font-size: var(--pm-text-md);
    font-weight: 600;
    color: var(--pm-color-text-muted);
    margin-top: var(--pm-space-3);
}
.pm-empty-body {
    margin-top: var(--pm-space-2);
    font-size: var(--pm-text-base);
    max-width: 48ch;
    margin-inline: auto;
    line-height: 1.6;
}

/* --- Reference formatter --------------------------------------------- */
/* The nine core elements of an MLA entry, and the shorter element lists of
   the other styles, are the point of the page: a reader who sees the order
   and the punctuation together stops treating a style as arbitrary. */
.pm-chain { display: grid; gap: var(--pm-space-2); }
.pm-chain-item {
    display: grid;
    grid-template-columns: 1.6rem 1fr;
    gap: var(--pm-space-3);
    padding: var(--pm-space-3) var(--pm-space-4);
    border: 1px solid var(--pm-color-border);
    border-left: 2px solid var(--pm-fill-accent-24);
    border-radius: var(--pm-radius-sm);
    background: var(--pm-color-surface-sunken);
    animation: pm-slide var(--pm-motion-enter) both;
    animation-delay: calc(var(--pm-step, 0) * var(--pm-motion-stagger));
}
.pm-chain-num {
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-xs);
    color: var(--pm-color-accent);
    padding-top: 2px;
}
.pm-chain-name {
    font-size: var(--pm-text-base);
    font-weight: 600;
    color: var(--pm-color-text);
}
.pm-chain-rule {
    margin-top: var(--pm-space-1);
    font-size: var(--pm-text-sm);
    line-height: 1.55;
    color: var(--pm-color-text-muted);
}

/* A formatted reference list, set the way it is set on paper: reading serif,
   hanging indent, one entry per block. */
.pm-reflist { display: grid; gap: var(--pm-space-4); }
.pm-refline {
    font-family: var(--pm-font-text);
    font-size: 1.0625rem;
    line-height: 1.7;
    color: var(--pm-color-text);
    padding-left: var(--pm-space-8);
    text-indent: calc(var(--pm-space-8) * -1);
    animation: pm-rise var(--pm-motion-enter) both;
    animation-delay: calc(var(--pm-step, 0) * var(--pm-motion-stagger));
}
.pm-refline em { font-style: italic; }
.pm-refmark {
    font-family: var(--pm-font-mono);
    font-size: var(--pm-text-sm);
    color: var(--pm-color-accent);
    margin-right: var(--pm-space-2);
}
.pm-refgap {
    display: block;
    margin-top: var(--pm-space-1);
    text-indent: 0;
    font-family: var(--pm-font-ui);
    font-size: var(--pm-text-xs);
    color: var(--pm-color-caution);
}

/* --- Motion ----------------------------------------------------------- */
@keyframes pm-rise {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: none; }
}
@keyframes pm-slide {
    from { opacity: 0; transform: translateX(-10px); }
    to { opacity: 1; transform: none; }
}
@keyframes pm-meter-grow {
    from { width: 0%; }
    to { width: var(--pm-meter, 0%); }
}
@keyframes pm-flow-advance {
    from { width: var(--pm-from, 0%); }
    to { width: var(--pm-to, 0%); }
}
@keyframes pm-flow-sweep {
    from { transform: translateX(-100%); }
    to { transform: translateX(100%); }
}
@keyframes pm-flow-pulse {
    0% { box-shadow: 0 0 0 0 var(--pm-fill-accent-24); }
    70% { box-shadow: 0 0 0 10px var(--pm-fill-accent-00); }
    100% { box-shadow: 0 0 0 0 var(--pm-fill-accent-00); }
}
@keyframes pm-flow-beacon {
    0%, 100% { opacity: 0.35; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1.15); }
}

/* Motion here is explanation, never decoration, so removing it removes
   nothing a reader needs. */
@media (prefers-reduced-motion: reduce) {
    .pm-card,
    .pm-meter-fill,
    .pm-flow,
    .pm-flow-fill,
    .pm-flow-step,
    .pm-flow-node,
    .pm-flow-beacon,
    .pm-chain-item,
    .pm-refline {
        animation: none !important;
    }
    .pm-flow.is-live .pm-flow-rail::after { display: none; }
    .pm-meter-fill { width: var(--pm-meter, 0%); }
    .pm-flow-fill { width: var(--pm-to, 0%); }
}

@media (max-width: 640px) {
    .pm-card { grid-template-columns: 1fr; gap: var(--pm-space-2); }
    .pm-card-head { flex-direction: column; gap: var(--pm-space-2); }
    .pm-def { grid-template-columns: 1fr; gap: var(--pm-space-1); }
    .pm-field { grid-template-columns: 1fr; gap: var(--pm-space-1); }
    .pm-flow-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--pm-space-4); }
}
"""


def build_stylesheet() -> str:
    """Assemble the complete stylesheet.

    Returns:
        The CSS text, without the enclosing ``<style>`` tags.
    """
    return f"{_foundations()}\n{_chrome()}\n{_components()}"


def inject_custom_css() -> None:
    """Inject the PaperMint stylesheet into the running app.

    Call once, immediately after ``st.set_page_config``.
    """
    st.markdown(f"<style>{build_stylesheet()}</style>", unsafe_allow_html=True)


__all__ = ["build_stylesheet", "inject_custom_css"]
