"""Theme tokens, global CSS, and chart palettes.

The CSS here is copied verbatim from the original app.py. Base rules are
injected first, then the per-theme token block overrides them. Keep that
order: reversing it makes the token colors lose to the base defaults.
"""

from __future__ import annotations

import streamlit as st


def active_theme() -> str:
    try:
        return getattr(st.context.theme, "type", None) or "light"
    except Exception:
        return "light"


BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
    --bg: #f6f8fb;
    --surface: #ffffff;
    --surface-alt: #eef4fb;
    --border: #d8e0ea;
    --border-strong: #91a4ba;
    --text: #10243e;
    --text-muted: #53657b;
    --primary: #1688e8;
    --accent-soft: #dceeff;
    --btn-bg: #1688e8;
    --btn-fg: #ffffff;
    --btn-hover: #0d6dbf;
    --tier-1: #5b34a8;
    --tier-2: #9a5a00;
    --tier-3: #1f5fd0;
    --tier-4: #0e7068;
    --tier-5: #51658a;
    --radius: 14px;
}
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"] { right: .75rem; top: .35rem; }
[data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1440px; padding: 2.25rem 2rem 3rem; }
section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] .block-container { padding: 1.25rem .9rem; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; color: var(--text) !important; margin-bottom: .25rem !important; }
h2, h3 { font-size: 1rem !important; font-weight: 600 !important; color: var(--text) !important; }
p, span, label { color: var(--text-muted); }
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
[data-testid="stMetricLabel"] { font-size: .72rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; }
[data-testid="stMetricLabel"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; line-height: 1.3; }
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: var(--text); }
[data-testid="stMetricValue"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
[data-testid="stHeading"] *, h3 { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.stPlotlyChart { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); padding: .5rem; }
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.section-title { font-size: .7rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .08em; margin: 1.5rem 0 .75rem; }
.note-box { background: var(--surface-alt); border-left: 4px solid var(--primary); padding: .75rem 1rem; border-radius: 0 var(--radius) var(--radius) 0; font-size: .85rem; color: var(--text); margin: 1rem 0; }
.user-chip { min-height: 44px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: flex-start; gap: .15rem; padding: .5rem .75rem; background: var(--surface); border: 1px solid var(--border-strong); border-radius: 8px; margin-top: 1.75rem; }
.user-role { font-size: .85rem; font-weight: 600; color: var(--text); }
.user-scope { font-size: .7rem; color: var(--text-muted); }
div[data-testid="stForm"] { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }
.stButton>button { min-height: 44px; background: var(--btn-bg); color: var(--btn-fg) !important; border: none; border-radius: 9px; font-weight: 600; padding: .5rem 1.25rem; }
.stButton>button:hover { background: var(--btn-hover); color: var(--btn-fg); }
.stButton>button p, .stButton>button span { color: inherit !important; }
.nav-control [data-baseweb="segmented-control"] { width: 100%; background: var(--surface-alt); border: 1px solid var(--border); padding: .2rem; border-radius: 9px; }
.nav-control [data-baseweb="segment"] { min-height: 34px; color: var(--text-muted); font-size: .78rem; }
.nav-control [data-baseweb="segment"][aria-checked="true"] { background: var(--primary); color: #173B73; }
.sidebar-brand { padding: .4rem .7rem 1.25rem; color: var(--text); font-weight: 700; font-size: 1.05rem; }
.sidebar-label { padding: 1.1rem .7rem .35rem; color: var(--text-muted); font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; }
.stDownloadButton>button { background: var(--surface); color: var(--text) !important; border: 1px solid var(--border); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput input, [data-baseweb="input"], [data-baseweb="select"]>div { background: var(--input-bg) !important; color: var(--input-text) !important; border: 1px solid var(--input-outline) !important; border-radius: 8px; }
.stTextInput input::placeholder { color: var(--input-text) !important; opacity: .7; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background: var(--surface) !important; color: var(--text) !important; }
[data-baseweb="popover"] *, [data-baseweb="menu"] *, [role="listbox"] *, [data-baseweb="select"] * { color: var(--input-text) !important; }
[data-baseweb="select"] [data-testid="stMarkdownContainer"], [data-baseweb="select"] [class*="placeholder"], [data-baseweb="select"] input::placeholder { color: var(--input-text) !important; opacity: .78 !important; }
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea,
[data-baseweb="input"] input, [data-baseweb="base-input"] input, [data-baseweb="textarea"] textarea,
[data-baseweb="select"] [data-baseweb="input"] input { color: var(--input-text) !important; -webkit-text-fill-color: var(--input-text) !important; caret-color: var(--input-text) !important; }
[data-baseweb="input"] input::placeholder, [data-baseweb="base-input"] input::placeholder, [data-baseweb="textarea"] textarea::placeholder { color: var(--input-text) !important; -webkit-text-fill-color: var(--input-text) !important; opacity: .7 !important; }
[data-baseweb="select"] [class*="singleValue"], [data-baseweb="select"] [class*="SingleValue"] { color: var(--input-text) !important; -webkit-text-fill-color: var(--input-text) !important; }
.stMultiSelectTagsContainer, .stMultiSelectTagsContainer *, .stMultiSelectTagsContainer svg { color: var(--tag-text) !important; fill: var(--tag-text) !important; -webkit-text-fill-color: var(--tag-text) !important; }
[aria-selected="true"], [data-baseweb="option"][aria-selected="true"] { background: var(--option-bg) !important; color: var(--option-text) !important; -webkit-text-fill-color: var(--option-text) !important; }
.stAlert { background: var(--surface-alt); border-color: var(--border); }
.stAlert [data-testid="stAlertContent"] { color: var(--text) !important; }
.stAlert[data-testid="stAlert"] { color: var(--text) !important; background: var(--surface-alt) !important; border-color: var(--border-strong) !important; }
.stAlert[data-testid="stAlert"] svg { color: var(--primary) !important; fill: var(--primary) !important; }
.stException { background: var(--surface-alt); color: var(--text); }
.stDownloadButton>button { border-color: var(--border-strong); }
:focus-visible { outline: 2px solid var(--primary) !important; outline-offset: 2px !important; }
</style>
"""

THEME_TOKENS = {
    "light": "--bg:#e7f3ff;--surface:#ffffff;--surface-alt:#d9edff;--border:#b8d4ed;--border-strong:#8fb5d8;--text:#173b73;--text-muted:#365985;--primary:#bde0fe;--accent-soft:#d9edff;--input-bg:#ffffff;--input-text:#173b73;--input-outline:#9bb3cc;--tag-bg:#173b73;--tag-text:#ffffff;--option-bg:#bde0fe;--option-text:#173b73;--btn-bg:#bde0fe;--btn-fg:#173b73;--btn-hover:#a7d3f5;",
    "dark": "--bg:#0b1f3a;--surface:#173b73;--surface-alt:#102d55;--border:#315783;--border-strong:#6b93c4;--text:#ffffff;--text-muted:#d6e5f7;--primary:#bde0fe;--accent-soft:#102d55;--input-bg:#2b5a96;--input-text:#ffffff;--input-outline:#ffffff;--tag-bg:#173b73;--tag-text:#ffffff;--option-bg:#2b5a96;--option-text:#ffffff;--btn-bg:#bde0fe;--btn-fg:#173b73;--btn-hover:#d5ecff;",
}


def apply_theme(theme: str) -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>:root {{{THEME_TOKENS.get(theme, THEME_TOKENS['light'])}}}</style>", unsafe_allow_html=True)


CHART_LIGHT = {
    "surface": "#ffffff", "text": "#365985", "title": "#173b73",
    "grid": "#d8e8f5", "zero": "#9bb3cc", "line": "#173b73",
    "baseline": "#5b34a8", "sensitivity": "#9a5a00",
    "tiers": {
        "Priority screening": "#5b34a8", "Beneish flag": "#9a5a00",
        "Anomaly flag": "#1f5fd0", "Low priority": "#0e7068",
        "Insufficient data / not calculable": "#51658a",
    },
}
CHART_DARK = {
    "surface": "#102d55", "text": "#c9d9ef", "title": "#f4f8ff",
    "grid": "#315783", "zero": "#6b93c4", "line": "#bde0fe",
    "baseline": "#c3a6f2", "sensitivity": "#e8b571",
    "tiers": {
        "Priority screening": "#c3a6f2", "Beneish flag": "#e8b571",
        "Anomaly flag": "#7db6f5", "Low priority": "#5fd3c4",
        "Insufficient data / not calculable": "#9fb4d4",
    },
}


def chart_palette() -> dict:
    """Pick chart colors from the active Streamlit theme."""
    try:
        if getattr(st.context.theme, "type", None) == "dark":
            return CHART_DARK
    except Exception:
        pass
    return CHART_LIGHT
