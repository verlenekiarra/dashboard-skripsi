from __future__ import annotations

import streamlit as st


def active_theme() -> str:
    try:
        return getattr(st.context.theme, "type", None) or "light"
    except Exception:
        return "light"


BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {
    --bg: #f3f7fb; --surface: #ffffff; --surface-2: #eaf1f7;
    --border: #cbd9e5; --border-strong: #8ca8bd;
    --text: #10243e; --muted: #536b80; --primary: #1769aa;
    --cyan: #0f9fad; --violet: #6554c0; --coral: #bd4d4b;
    --mint: #167a68; --yellow: #966000; --focus: #0f748c;
    --input: #ffffff; --nav: #e8f0f6; --nav-hover: #dce9f2;
    --shadow: 0 8px 22px rgba(16, 36, 62, .08);
}
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: linear-gradient(135deg, var(--bg) 0%, var(--bg-2) 52%, var(--bg-3) 100%); color: var(--text); }
.stApp:before { content:""; position:fixed; inset:0; pointer-events:none; background:radial-gradient(circle at 88% 8%, var(--glow), transparent 28%); opacity:.5; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1480px; padding: 2rem clamp(1rem, 3vw, 3rem) 3rem; animation: page-enter .35s ease both; }
[data-testid="column"] { min-width: 0 !important; }
h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -.025em; }
h1 { font-size: clamp(1.6rem, 2.4vw, 2.4rem) !important; font-weight: 800 !important; }
h2 { font-size: clamp(1.2rem, 1.8vw, 1.6rem) !important; font-weight: 800 !important; }
h3 { font-size: 1rem !important; font-weight: 700 !important; }
p, span, label { color: var(--muted); }
section[data-testid="stSidebar"] { background:color-mix(in srgb, var(--surface) 88%, transparent); backdrop-filter:blur(16px); border-right:1px solid var(--border); }
section[data-testid="stSidebar"] .block-container { padding: 1.2rem .85rem 2rem; }
.sidebar-brand { display:flex; align-items:center; gap:.65rem; padding:.35rem .55rem 1.1rem; color:var(--text); font-size:1.05rem; font-weight:800; }
.brand-mark { display:grid; place-items:center; width:34px; height:34px; border-radius:10px; background:var(--cyan); color:var(--text); font-size:.7rem; font-weight:800; letter-spacing:.06em; }
.role-badge { display:inline-block; margin:0 .55rem 1rem; padding:.28rem .62rem; border:1px solid var(--border); border-radius:7px; background:var(--surface-2); color:var(--text); font-size:.7rem; font-weight:800; }
.sidebar-label, .section-title { color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
.sidebar-label { padding:.65rem .55rem .4rem; }
.section-title { margin:1.5rem 0 .7rem; }
.nav-group-label { padding:1rem .75rem .35rem; color:var(--muted); font-size:.66rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
.nav-divider { height:1px; margin:1.1rem .5rem .8rem; background:var(--border); }
section[data-testid="stSidebar"] [class*="st-key-nav"] { gap:.15rem !important; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button { width:100%; min-height:40px; justify-content:flex-start !important; padding:.5rem .75rem !important; border:0 !important; border-radius:12px !important; background:transparent !important; box-shadow:none !important; color:var(--muted) !important; font-size:.86rem !important; font-weight:600 !important; transition:background .18s ease, color .18s ease; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button > div { justify-content:flex-start !important; gap:.7rem; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button p { text-align:left; color:inherit !important; font-size:inherit !important; font-weight:inherit !important; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button [data-testid="stIconMaterial"] { color:inherit !important; font-size:1.25rem !important; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button:hover { background:var(--nav-soft) !important; color:var(--text) !important; transform:none; }
section[data-testid="stSidebar"] [class*="st-key-nav"] button:focus-visible { outline:2px solid var(--focus) !important; outline-offset:1px !important; }
section[data-testid="stSidebar"] [class*="st-key-navactive_"] button { background:var(--nav-active-bg) !important; color:var(--text) !important; font-weight:700 !important; }
section[data-testid="stSidebar"] [class*="st-key-navparent_"][class*="_active"] button { background:var(--nav-active-bg) !important; color:var(--text) !important; }
section[data-testid="stSidebar"] [class*="st-key-navparent_"] button { position:relative; padding-right:2.2rem !important; }
section[data-testid="stSidebar"] [class*="st-key-navparent_"] button:after { content:""; position:absolute; right:1rem; top:50%; width:6px; height:6px; border-right:1.6px solid currentColor; border-bottom:1.6px solid currentColor; transform:translateY(-70%) rotate(45deg); transition:transform .18s ease; }
section[data-testid="stSidebar"] [class*="st-key-navparent_open"] button:after { transform:translateY(-25%) rotate(-135deg); }
.st-key-nav_children { position:relative; margin:.15rem 0 .35rem 1.45rem; padding-left:1rem; }
.st-key-nav_children:before { content:""; position:absolute; left:0; top:0; bottom:20px; border-left:1.5px solid var(--nav-line); }
.st-key-nav_children [class*="st-key-navitem_"], .st-key-nav_children [class*="st-key-navactive_"] { position:relative; }
.st-key-nav_children [class*="st-key-navitem_"]:before, .st-key-nav_children [class*="st-key-navactive_"]:before { content:""; position:absolute; left:-1rem; top:2px; width:.8rem; height:18px; border-left:1.5px solid var(--nav-line); border-bottom:1.5px solid var(--nav-line); border-bottom-left-radius:9px; }
.st-key-nav_children button { min-height:36px !important; font-size:.82rem !important; }
.st-key-sign_out button {  color:var(--primary) !important; border:1px solid var(--signout-border) !important; box-shadow:none !important; }
.header-band { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:flex-end; gap:1rem; margin:0 0 1.1rem; padding:1.3rem 1.5rem; border-radius:16px; background:linear-gradient(120deg,#0b2235 0%,#14507d 55%,#0f7f8c 100%); box-shadow:0 14px 32px rgba(11,34,53,.18); position:relative; overflow:hidden; }
.header-band:after { content:""; position:absolute; right:-60px; top:-90px; width:220px; height:220px; border-radius:50%; border:1px solid rgba(142,223,224,.35); box-shadow:0 0 0 26px rgba(142,223,224,.06); pointer-events:none; }
.hb-main { min-width:0; position:relative; z-index:1; }
.hb-kicker { color:#8edfe0 !important; font-size:.68rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
.hb-title { margin:.25rem 0 .6rem !important; padding:0 !important; color:#f5fbff !important; font-size:clamp(1.4rem,2.4vw,2rem) !important; }
.hb-chips { display:flex; flex-wrap:wrap; gap:.4rem; }
.hb-chip { padding:.2rem .6rem; border-radius:999px; background:rgba(255,255,255,.14); color:#e6f3fb !important; font-size:.7rem; font-weight:700; }
.hb-chip-muted { color:#b9d3e4 !important; }
.hb-stats { display:flex; flex-wrap:wrap; gap:.6rem; position:relative; z-index:1; }
.hb-stat { min-width:110px; padding:.6rem .85rem; border-radius:11px; background:rgba(255,255,255,.1); border-top:3px solid var(--hb-accent); }
.hb-stat span { display:block; color:#b9d3e4 !important; font-size:.64rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
.hb-stat strong { display:block; color:#fff; font-size:1.15rem; font-weight:800; font-variant-numeric:tabular-nums; }
.hb-blue { --hb-accent:#7cc0f5; } .hb-teal { --hb-accent:#5fe0cf; } .hb-violet { --hb-accent:#b9a8ff; }
.stButton>button:disabled, .stFormSubmitButton>button:disabled { background:var(--disabled-bg) !important; color:var(--disabled-text) !important; border:1px dashed var(--border-strong) !important; box-shadow:none !important; transform:none !important; cursor:not-allowed; }
.st-key-data-management-delete button:not(:disabled) { background:#b42318 !important; color:#fff !important; }
.st-key-data-management-delete button:not(:disabled):hover { background:#8f1d14 !important; }
.st-key-sign_out button:hover { background:var(--nav-hover) !important; color:#fff !important; border-color:var(--nav-hover) !important; transform:none; }
.st-key-sign_out button p, .st-key-sign_out button span { color:inherit !important; }
.user-chip { min-height:44px; display:flex; flex-direction:column; justify-content:center; gap:.1rem; padding:.55rem .75rem; border:1px solid var(--border); border-radius:9px; background:var(--surface); }
.user-role { color:var(--text); font-size:.78rem; font-weight:800; }
.user-scope { color:var(--muted); font-size:.68rem; }
[data-testid="stMetric"], .modern-card, div[data-testid="stForm"] { background:var(--surface); border:1px solid var(--border); border-radius:12px; box-shadow:var(--shadow); }
[data-testid="stMetric"] { padding:1rem 1.1rem; border-top:3px solid var(--primary); transition:transform .2s ease, box-shadow .2s ease; }
[data-testid="stMetric"]:hover, .modern-card:hover { transform:translateY(-2px); box-shadow:0 12px 26px rgba(16,36,62,.12); }
[data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:.7rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; }
[data-testid="stMetricValue"] { color:var(--text) !important; font-size:1.55rem; font-weight:800; }
.modern-card { min-height:120px; padding:1rem 1.1rem; border-top:3px solid var(--card-accent, var(--primary)); transition:transform .2s ease, box-shadow .2s ease; }
.card-header { display:flex; justify-content:space-between; align-items:center; }
.card-title { color:var(--muted); font-size:.7rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; }
.card-icon-bubble { display:grid; place-items:center; width:30px; height:30px; border-radius:8px; background:var(--surface-2); color:var(--primary); font-weight:800; }
.card-value { margin:.35rem 0 .5rem; color:var(--text); font-size:1.7rem; font-weight:800; font-variant-numeric:tabular-nums; }
.card-pill { display:inline-block; padding:.2rem .5rem; border-radius:5px; background:var(--surface-2); color:var(--muted); font-size:.66rem; font-weight:700; }
.theme-warning { --card-accent:var(--yellow); } .theme-danger { --card-accent:var(--coral); }
.note-box { margin:1.25rem 0; padding:.85rem 1rem; border:1px solid var(--border); border-left:4px solid var(--cyan); border-radius:0 10px 10px 0; background:var(--surface-2); color:var(--text); font-size:.83rem; }
div[data-testid="stForm"] { padding:1.35rem; }
.stButton>button, .stFormSubmitButton>button { min-height:44px; border:0; border-radius:8px; background:var(--primary); color:#fff !important; font-weight:800; transition:transform .18s ease, background .18s ease, box-shadow .18s ease; }
.stButton>button p, .stButton>button span, .stFormSubmitButton>button p, .stFormSubmitButton>button span { color:inherit !important; }
.stButton>button:hover, .stFormSubmitButton>button:hover { background:#125487; transform:translateY(-1px); box-shadow:0 7px 15px rgba(23,105,170,.22); }
.stDownloadButton>button { min-height:44px; border:1px solid var(--border-strong); border-radius:8px; background:var(--surface); color:var(--text) !important; font-weight:700; }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput input, [data-baseweb="input"], [data-baseweb="select"]>div { background:var(--input) !important; color:var(--text) !important; border:1px solid var(--input-border) !important; border-radius:8px; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:var(--muted) !important; opacity:.7; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background:var(--surface) !important; color:var(--text) !important; }
[data-baseweb="popover"] *, [data-baseweb="menu"] *, [role="listbox"] *, [data-baseweb="select"] * { color:var(--text) !important; }
[data-baseweb="select"] [data-testid="stMarkdownContainer"], [data-baseweb="select"] [class*="placeholder"], [data-baseweb="select"] input::placeholder { color:var(--muted) !important; opacity:.78 !important; }
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea,
[data-baseweb="input"] input, [data-baseweb="base-input"] input, [data-baseweb="textarea"] textarea,
[data-baseweb="select"] [data-baseweb="input"] input { color:var(--text) !important; -webkit-text-fill-color:var(--text) !important; caret-color:var(--text) !important; }
[data-baseweb="input"] input::placeholder, [data-baseweb="base-input"] input::placeholder, [data-baseweb="textarea"] textarea::placeholder { color:var(--muted) !important; -webkit-text-fill-color:var(--muted) !important; opacity:.7 !important; }
[data-baseweb="select"] [class*="singleValue"], [data-baseweb="select"] [class*="SingleValue"] { color:var(--text) !important; -webkit-text-fill-color:var(--text) !important; }
.stMultiSelectTagsContainer, .stMultiSelectTagsContainer *, .stMultiSelectTagsContainer svg { color:var(--text) !important; fill:var(--text) !important; -webkit-text-fill-color:var(--text) !important; }
.stMultiSelectTagsContainer { background:var(--surface-2) !important; border-radius:7px; }
[aria-selected="true"], [data-baseweb="option"][aria-selected="true"] { background:var(--surface-2) !important; color:var(--text) !important; -webkit-text-fill-color:var(--text) !important; }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:10px; overflow:hidden; background:var(--surface); }
[data-testid="stDataFrame"] table { font-family:'Plus Jakarta Sans', sans-serif !important; }
[data-testid="stDataFrame"] th { background:var(--surface-2) !important; color:var(--text) !important; font-weight:800 !important; }
[data-testid="stDataFrame"] td { color:var(--text) !important; background:var(--surface) !important; }
.stPlotlyChart { margin-bottom:1rem; padding:.25rem !important; border:1px solid var(--border); border-radius:12px; background:var(--surface); overflow:hidden !important; }
.login-shell { padding:clamp(1.5rem, 5vw, 5rem) 0 2rem; }
.login-panel { min-height:430px; padding:clamp(1.4rem, 4vw, 3rem); border:1px solid var(--border); border-radius:18px; background:var(--surface); box-shadow:var(--shadow); }
.login-shell .stForm { min-height:430px; margin-top:.8rem; padding:clamp(1.4rem, 4vw, 3rem); border:1px solid var(--border-strong); border-radius:18px; background:var(--surface); box-shadow:0 16px 35px rgba(16,36,62,.12); }
.login-visual { min-height:430px; padding:clamp(1.4rem, 4vw, 3rem); border-radius:18px; background:#0b2235; overflow:hidden; position:relative; box-shadow:0 18px 45px rgba(8,31,49,.2); }
.login-visual:after { content:""; position:absolute; width:240px; height:240px; right:-65px; bottom:-80px; border:1px solid rgba(81,208,209,.55); border-radius:50%; box-shadow:0 0 0 30px rgba(81,208,209,.08), 0 0 0 60px rgba(81,208,209,.05); }
.login-kicker { color:#8edfe0; font-size:.68rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
.login-title { max-width:10ch; margin:1rem 0; color:#f5fbff !important; font-size:clamp(2rem, 4vw, 3.8rem) !important; line-height:1.02; }
.login-title *, .login-copy { color:#cfe1ef !important; }
.typed-line { min-height:1.6em; color:#8edfe0 !important; font-weight:600; }
.typed-line span { color:#8edfe0 !important; }
.typed-caret { display:inline-block; width:2px; height:1.05em; margin-left:2px; vertical-align:-.15em; background:#51d0d1; animation:blink-caret .8s step-end infinite; }
.magic-title { position:relative; display:inline; color:#f5fbff !important; }
.magic-title:after { content:"✦"; display:inline-block; margin-left:.12em; vertical-align:super; color:#51d0d1; font-size:.32em; line-height:0; animation:sparkle-pulse 2.4s ease-in-out infinite; }
@keyframes blink-caret { from, to { opacity:0 } 50% { opacity:1 } }
@keyframes sparkle-pulse { 0%, 100% { opacity:.35; transform:scale(.75) rotate(0deg); } 50% { opacity:1; transform:scale(1.2) rotate(18deg); } }
@keyframes page-enter { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }
:focus-visible { outline:3px solid var(--focus) !important; outline-offset:2px !important; }
@media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:.01ms !important; } }
@media (max-width: 760px) { .block-container { padding:1.15rem .8rem 2rem; } .login-shell { padding-top:1rem; } .login-visual { min-height:300px; } .login-title { font-size:2.25rem !important; }  .stPlotlyChart { padding:0 !important; } }
</style>
"""

THEME_TOKENS = {
    "light": "--bg:#c9e3f7;--bg-2:#b5d8f2;--bg-3:#c7eee7;--glow:rgba(23,105,170,.3);--page-gradient:linear-gradient(135deg,#9fcdef 0%,#dcecf9 48%,#b3e6dc 100%);--input-border:#4f7898;--signout-bg:#d3e6f5;--signout-border:#8fb3cf;--disabled-bg:#e3ecf3;--disabled-text:#4f6477;--surface:#ffffff;--surface-2:#eaf4fb;--border:#a9c8df;--border-strong:#6f96b4;--text:#10243e;--muted:#536b80;--primary:#1769aa;--cyan:#0f9fad;--focus:#0f748c;--input:#ffffff;--nav:#e8f0f6;--nav-card:#1f6fae;--nav-active:#10243e;--nav-hover:#287db4;--nav-soft:rgba(16,36,62,.06);--nav-active-bg:rgba(16,36,62,.09);--nav-line:#a9bccb;",
    "dark": "--input-border:#7093aa;--signout-bg:#15344b;--signout-border:#4a6a82;--disabled-bg:#15344b;--disabled-text:#b7cbdc;--bg:#081522;--bg-2:#0b1c2e;--bg-3:#082b32;--glow:rgba(81,208,209,.14);--page-gradient:linear-gradient(135deg,#081522 0%,#0b1c2e 55%,#082b32 100%);--surface:#10283c;--surface-2:#15344b;--border:#31536c;--border-strong:#7093aa;--text:#edf6ff;--muted:#b7cbdc;--primary:#5ca8e6;--cyan:#51d0d1;--focus:#8edfe0;--input:#15344b;--nav:#0d2234;--nav-card:#1f5f93;--nav-active:#071a32;--nav-hover:#2877ad;--nav-soft:rgba(237,246,255,.06);--nav-active-bg:rgba(237,246,255,.11);--nav-line:#4a6a82;",
}

CHART_LIGHT = {"surface": "#ffffff", "text": "#536b80", "title": "#10243e", "grid": "#dbe6ee", "zero": "#8ca8bd", "line": "#1769aa", "baseline": "#bd4d4b", "sensitivity": "#966000", "tiers": {"Priority screening": "#bd4d4b", "Beneish flag": "#966000", "Anomaly flag": "#6554c0", "Low priority": "#167a68", "Insufficient data / not calculable": "#536b80"}}
CHART_DARK = {"surface": "#10283c", "text": "#b7cbdc", "title": "#edf6ff", "grid": "#31536c", "zero": "#7093aa", "line": "#51d0d1", "baseline": "#f08a86", "sensitivity": "#f1c36b", "tiers": {"Priority screening": "#f08a86", "Beneish flag": "#f1c36b", "Anomaly flag": "#a99bef", "Low priority": "#66d4b2", "Insufficient data / not calculable": "#b7cbdc"}}


def apply_theme(theme: str) -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>:root {{{THEME_TOKENS.get(theme, THEME_TOKENS['light'])}}}</style>", unsafe_allow_html=True)


def chart_palette() -> dict:
    try:
        if getattr(st.context.theme, "type", None) == "dark":
            return CHART_DARK
    except Exception:
        pass
    return CHART_LIGHT
