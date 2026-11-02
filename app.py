from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.analytics.beneish import AnalysisConfig, BASELINE_THRESHOLD, SENSITIVITY_THRESHOLD, analyze
from src.auth.permissions import authenticate, create_user, ensure_admin_user, allowed
from src.data.database import create_mysql_engine
from src.data.io import export_csv, export_excel, read_upload, read_workbook_long
from src.data.repository import load_analysis, load_staging, read_analysis

st.set_page_config(page_title="Financial Risk Analytics", layout="wide", initial_sidebar_state="expanded")

try:
    ACTIVE_THEME = getattr(st.context.theme, "type", None) or "light"
except Exception:
    ACTIVE_THEME = "light"

st.markdown("""
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
.stButton>button { min-height: 44px; background: var(--btn-bg); color: var(--btn-fg); border: none; border-radius: 9px; font-weight: 600; padding: .5rem 1.25rem; }
.stButton>button:hover { background: var(--btn-hover); color: var(--btn-fg); }
.nav-control [data-baseweb="segmented-control"] { width: 100%; background: var(--surface-alt); border: 1px solid var(--border); padding: .2rem; border-radius: 9px; }
.nav-control [data-baseweb="segment"] { min-height: 34px; color: var(--text-muted); font-size: .78rem; }
.nav-control [data-baseweb="segment"][aria-checked="true"] { background: var(--primary); color: #173B73; }
.sidebar-brand { padding: .4rem .7rem 1.25rem; color: var(--text); font-weight: 700; font-size: 1.05rem; }
.sidebar-label { padding: 1.1rem .7rem .35rem; color: var(--text-muted); font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; }
.stDownloadButton>button { background: var(--surface); color: var(--text); border: 1px solid var(--border); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput input, [data-baseweb="input"], [data-baseweb="select"]>div { background: var(--input-bg) !important; color: var(--text) !important; border: 1px solid var(--input-outline) !important; border-radius: 8px; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background: var(--surface) !important; color: var(--text) !important; }
.stAlert { background: var(--surface-alt); border-color: var(--border); }
.stDownloadButton>button { border-color: var(--border-strong); }
:focus-visible { outline: 2px solid var(--primary) !important; outline-offset: 2px !important; }
</style>
""", unsafe_allow_html=True)

THEME_TOKENS = {
    "light": "--bg:#f8fafc;--surface:#ffffff;--surface-alt:#eef6ff;--border:#c8d7e8;--border-strong:#9bb3cc;--text:#173b73;--text-muted:#365985;--primary:#bde0fe;--accent-soft:#e7f3ff;--input-bg:#ffffff;--input-outline:#9bb3cc;--btn-bg:#bde0fe;--btn-fg:#173b73;--btn-hover:#a7d3f5;",
    "dark": "--bg:#0b1f3a;--surface:#102d55;--surface-alt:#173b73;--border:#315783;--border-strong:#6b93c4;--text:#f4f8ff;--text-muted:#c9d9ef;--primary:#bde0fe;--accent-soft:#173b73;--input-bg:#dff0ff;--input-outline:#ffffff;--btn-bg:#bde0fe;--btn-fg:#173b73;--btn-hover:#d5ecff;",
}
st.markdown(f"<style>:root {{{THEME_TOKENS.get(ACTIVE_THEME, THEME_TOKENS['light'])}}}</style>", unsafe_allow_html=True)


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


NAV_BY_ROLE: dict[str, list[str]] = {
    "Administrator": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis", "Analysis Results", "Data Management", "Upload Financial Data", "User Management"],
    "Stakeholder": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis", "Upload Financial Data"],
    "User": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis"],
}


def load_data() -> pd.DataFrame:
    if "financial_data" in st.session_state:
        return st.session_state["financial_data"]
    try:
        data = read_analysis(create_mysql_engine())
        if not data.empty:
            st.session_state["financial_data"] = data
            st.session_state["data_source"] = "MySQL"
            return data
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        pass
    default_path = Path(".agents/skills/docs/skripsi_rawwwwwwwww_ajajaja.xlsx")
    if default_path.exists():
        try:
            source = BytesIO(default_path.read_bytes())
            source.name = default_path.name
            data = read_upload(source)
            st.session_state["financial_data"] = data
            st.session_state["data_source"] = "Local workbook"
            return data
        except (AttributeError, OSError, ValueError):
            pass
    return pd.DataFrame()


def render_login() -> str | None:
    if st.session_state.get("authenticated_role"):
        return st.session_state["authenticated_role"]
    try:
        ensure_admin_user(create_mysql_engine())
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        pass
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("Financial Risk Analytics")
        st.caption("Dashboard analitik risiko manipulasi laporan keuangan")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width="stretch")
        if submitted:
            role = authenticate(username, password)
            if role:
                st.session_state["authenticated_role"] = role
                st.rerun()
            st.error("Username atau password tidak valid.")
        if not os.getenv("APP_USERS_JSON"):
            st.markdown('', unsafe_allow_html=True)
    return None


def render_sidebar(role: str) -> str:
    with st.sidebar:
        st.markdown(f'<div class="sidebar-brand">{role}</div>', unsafe_allow_html=True)
        if st.button("Sign out", width="stretch"):
            st.session_state.pop("authenticated_role", None)
            st.rerun()
        st.markdown("---")
        pages = NAV_BY_ROLE.get(role, NAV_BY_ROLE["User"])
        current = st.session_state.get("active_page", pages[0])
        if current not in pages:
            current = pages[0]
        st.markdown('<div class="sidebar-label">Navigation</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-control">', unsafe_allow_html=True)
        page = st.segmented_control("Navigation", pages, default=current, label_visibility="collapsed", key="sidebar_navigation")
        st.markdown('</div>', unsafe_allow_html=True)
        page = page or current
        st.session_state["active_page"] = page
        st.markdown('<div class="sidebar-label">Account</div>', unsafe_allow_html=True)
        if allowed(role, "export") and "analysis_data" in st.session_state:
            st.markdown('<p class="section-title">Export</p>', unsafe_allow_html=True)
            export_frame = st.session_state["analysis_data"]
            st.download_button("CSV", export_csv(export_frame), "risk_analysis.csv", "text/csv", width="stretch")
            st.download_button("Excel", export_excel(export_frame), "risk_analysis.xlsx", width="stretch")
    return page


def render_header(data: pd.DataFrame, role: str, page: str) -> pd.DataFrame:
    title, year_col, company_col, user_col = st.columns([2.1, 1.2, 1.5, 1.1])
    with title:
        st.markdown("### Analytical Dashboard")
        st.caption(f"{page} · Threshold {BASELINE_THRESHOLD}")
    with year_col:
        years = sorted(data["FiscalYear"].dropna().astype(int).unique().tolist())
        selected_years = st.multiselect("Year", years, default=years, placeholder="Filter by year")
    with user_col:
        st.markdown(f'<div class="user-chip"><span class="user-role">{role}</span><span class="user-scope">{"Full access" if role == "Administrator" else "Upload and export" if role == "Stakeholder" else "View only"}</span></div>', unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns([1.2, 1.2, 1.5])
    with filter_col1:
        subsectors = sorted(data["SubSector"].dropna().astype(str).unique().tolist()) if "SubSector" in data else []
        selected_subsectors = st.multiselect("Subsector", subsectors, placeholder="All subsectors")
    with filter_col2:
        statuses = sorted(data["RiskLabel"].dropna().astype(str).unique().tolist()) if "RiskLabel" in data else []
        selected_statuses = st.multiselect("Status", statuses, placeholder="All statuses")
    with company_col:
        tickers = sorted(data["Ticker"].dropna().unique().tolist())
        selected_tickers = st.multiselect("Company", tickers, placeholder="Filter by company code")
    filtered = data[data["FiscalYear"].isin(selected_years)] if selected_years else data.iloc[0:0]
    if selected_tickers:
        filtered = filtered[filtered["Ticker"].isin(selected_tickers)]
    if selected_subsectors:
        filtered = filtered[filtered["SubSector"].isin(selected_subsectors)]
    if selected_statuses:
        filtered = filtered[filtered["RiskLabel"].isin(selected_statuses)]
    active = []
    if selected_years:
        active.append(f"{len(selected_years)} year(s)")
    if selected_tickers:
        active.append(f"{len(selected_tickers)} company(s)")
    if selected_subsectors:
        active.append(f"{len(selected_subsectors)} subsector(s)")
    if selected_statuses:
        active.append(f"{len(selected_statuses)} status(es)")
    st.caption("Active filter: " + (", ".join(active) if active else "none"))
    st.caption(f"Data source: {st.session_state.get('data_source', 'Unknown')}")
    return filtered


def render_kpis(data: pd.DataFrame) -> None:
    total_companies = data["Ticker"].nunique()
    total_obs = len(data)
    beneish_flags = int(data["RiskLabel"].eq("Potential earnings manipulation").sum())
    anomalies = int(data["AnomalyLabel"].eq(-1).sum())
    priority = int(data["ScreeningPriority"].eq("Priority screening").sum())
    avg_mscore = data["MScore"].mean()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Companies", f"{total_companies:,}")
    c2.metric("Observations", f"{total_obs:,}")
    c3.metric("Beneish Flags", f"{beneish_flags:,}", help=f"M-Score > {BASELINE_THRESHOLD}")
    c4.metric("Anomalies", f"{anomalies:,}", help="Isolation Forest label -1")


def render_mscore_trend(data: pd.DataFrame) -> None:
    trend = data.groupby("FiscalYear", as_index=False).agg({"MScore": "mean"}).dropna()
    if trend.empty:
        st.info("Tidak cukup data untuk trend chart.")
        return
    palette = chart_palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["FiscalYear"], y=trend["MScore"], mode="lines+markers", name="Avg M-Score", line=dict(color=palette["line"], width=2), marker=dict(size=8)))
    fig.add_hline(y=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"], annotation_text="Threshold -1.78")
    fig.add_hline(y=SENSITIVITY_THRESHOLD, line_dash="dot", line_color=palette["sensitivity"], annotation_text="Sensitivity -2.22")
    fig.update_layout(title="Beneish M-Score Analysis by Year", height=340, margin=dict(l=20, r=20, t=55, b=20), xaxis_title="Year", yaxis_title="M-Score", plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"], font=dict(family="Inter", color=palette["text"]), title_font=dict(color=palette["title"], size=15))
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    st.plotly_chart(fig, width="stretch")


def render_scatter(data: pd.DataFrame) -> None:
    plot_data = data.dropna(subset=["MScore", "AnomalyScore"]).copy()
    if plot_data.empty:
        st.info("Tidak cukup data untuk scatter plot.")
        return
    palette = chart_palette()
    fig = px.scatter(plot_data, x="AnomalyScore", y="MScore", color="ScreeningPriority", hover_name="Ticker", hover_data=["FiscalYear", "RiskLabel", "AnomalyStatus"], color_discrete_map=palette["tiers"])
    fig.add_hline(y=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"])
    fig.update_layout(title="M-Score vs Anomaly Score", height=340, margin=dict(l=20, r=20, t=55, b=20), xaxis_title="Anomaly Score", yaxis_title="Beneish M-Score", legend_title="Status", plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"], font=dict(family="Inter", color=palette["text"]), title_font=dict(color=palette["title"], size=15), legend=dict(orientation="h", yanchor="bottom", y=-0.32, xanchor="left", x=0))
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    st.plotly_chart(fig, width="stretch")


def chart_layout(fig: go.Figure, title: str, palette: dict, height: int = 340) -> go.Figure:
    fig.update_layout(
        title=title, height=height, margin=dict(l=20, r=20, t=55, b=25),
        plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"],
        font=dict(family="Inter", color=palette["text"]),
        title_font=dict(color=palette["title"], size=15),
    )
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    return fig


def render_mscore_distribution(data: pd.DataFrame) -> None:
    values = data.dropna(subset=["MScore"])
    if values.empty:
        st.info("Belum ada M-Score yang dapat divisualisasikan.")
        return
    palette = chart_palette()
    fig = px.histogram(values, x="MScore", nbins=24, color_discrete_sequence=[palette["line"]])
    fig.add_vline(x=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"], annotation_text="Threshold")
    st.plotly_chart(chart_layout(fig, "Distribusi Beneish M-Score", palette), width="stretch")


def render_anomaly_distribution(data: pd.DataFrame) -> None:
    values = data.dropna(subset=["AnomalyScore"])
    if values.empty:
        st.info("Belum ada Anomaly Score yang dapat divisualisasikan.")
        return
    palette = chart_palette()
    fig = px.histogram(values, x="AnomalyScore", nbins=24, color_discrete_sequence=[palette["line"]])
    st.plotly_chart(chart_layout(fig, "Distribusi Anomaly Score", palette), width="stretch")


def screening_category(data: pd.DataFrame) -> pd.Series:
    beneish = data["RiskLabel"].eq("Potential earnings manipulation")
    anomaly = data["AnomalyLabel"].eq(-1)
    return pd.Series([
        "Terindikasi oleh Beneish dan anomaly" if b and a else "Terindikasi oleh Beneish saja" if b else "Terdeteksi anomaly saja" if a else "Tidak terindikasi manipulasi oleh kedua metode"
        for b, a in zip(beneish.fillna(False), anomaly.fillna(False))
    ], index=data.index)


def render_screening_matrix(data: pd.DataFrame) -> None:
    categories = screening_category(data).value_counts().rename_axis("Screening category").reset_index(name="Observations")
    st.dataframe(categories, width="stretch", hide_index=True)
    st.caption("Tidak terindikasi manipulasi oleh kedua metode berarti observasi tidak melewati threshold Beneish dan berlabel normal oleh Isolation Forest. Ini bukan bukti bahwa manipulasi tidak mungkin terjadi.")
    palette = chart_palette()
    fig = px.bar(categories, x="Screening category", y="Observations", color="Screening category", color_discrete_sequence=[palette["line"], palette["baseline"], palette["sensitivity"], palette["tiers"]["Low priority"]])
    st.plotly_chart(chart_layout(fig, "Independent screening results", palette), width="stretch")


RANK_COLUMN_CONFIG = {
    "RiskRank": st.column_config.NumberColumn("Rank", format="%d", help="Review order: screening tier, then M-Score, then anomaly score"),
    "MScore": st.column_config.NumberColumn("M-Score", format="%.4f"),
    "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f"),
    "RiskLabel": "M-Score Status",
    "AnomalyStatus": "Anomaly Status",
    "ScreeningPriority": "Risk Status",
}


def render_priority_table(data: pd.DataFrame) -> None:
    ranked = data.dropna(subset=["RiskRank"]).sort_values("RiskRank").head(5)
    st.markdown('<p class="section-title">Top 5 Company List by Risk</p>', unsafe_allow_html=True)
    if ranked.empty:
        st.info("Belum ada observasi yang dapat diberi peringkat. Semua baris berstatus insufficient data.")
        return
    columns = ["RiskRank", "Ticker", "CompanyName", "FiscalYear", "MScore", "AnomalyScore", "ScreeningPriority"]
    st.dataframe(ranked[[c for c in columns if c in ranked.columns]], width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)
    st.caption("Peringkat adalah urutan review bertingkat, bukan skor komposit atau bukti fraud.")


def render_companies_table(data: pd.DataFrame) -> None:
    st.markdown('<p class="section-title">Companies List</p>', unsafe_allow_html=True)
    display_cols = ["RiskRank", "Ticker", "CompanyName", "FiscalYear", "MScore", "RiskLabel", "AnomalyScore", "AnomalyStatus"]
    available = [c for c in display_cols if c in data.columns]
    table = data[available].sort_values("RiskRank", na_position="last") if "RiskRank" in available else data[available]
    st.dataframe(table, width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)


def render_overview(data: pd.DataFrame) -> None:
    render_kpis(data)
    col1, col2 = st.columns(2)
    with col1:
        render_mscore_trend(data)
    with col2:
        render_anomaly_distribution(data)
    st.markdown('<p class="section-title">Independent screening comparison</p>', unsafe_allow_html=True)
    render_screening_matrix(data)
    col3, col4 = st.columns([1.5, 1])
    with col3:
        render_companies_table(data)
    with col4:
        render_priority_table(data)


def render_beneish_page(data: pd.DataFrame) -> None:
    st.markdown("### Beneish M-Score Analysis")
    st.caption(f"Threshold: M-Score > {BASELINE_THRESHOLD} indicates potential earnings manipulation")
    valid = data.dropna(subset=["MScore"])
    flags = int(valid["RiskLabel"].eq("Potential earnings manipulation").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Observations analysed", f"{len(valid):,}")
    c2.metric("Above threshold", f"{flags:,}")
    c3.metric("Flag proportion", f"{flags / len(valid):.1%}" if len(valid) else "N/A")
    col1, col2 = st.columns(2)
    with col1:
        render_mscore_distribution(data)
    with col2:
        render_mscore_trend(data)
    st.info("Delapan indeks adalah sinyal dalam model Beneish. Status screening bukan bukti manipulasi laporan keuangan.")
    st.caption("DSRI: piutang terhadap penjualan. GMI: gross margin. AQI: kualitas aset. SGI: pertumbuhan penjualan. DEPI: depresiasi. SGAI: beban penjualan dan administrasi. LVGI: leverage. TATA: akrual terhadap aset.")
    st.markdown('<p class="section-title">Beneish indices</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Detailed Indices</p>', unsafe_allow_html=True)
    index_cols = ["Ticker", "CompanyName", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "MScore", "RiskLabel"]
    available = [c for c in index_cols if c in data.columns]
    st.dataframe(data[available].sort_values("MScore", ascending=False), width="stretch", hide_index=True)


def render_anomaly_page(data: pd.DataFrame) -> None:
    st.markdown("### Anomaly Detection")
    st.caption("Isolation Forest identifies unusual financial patterns. Higher score = more anomalous.")
    total_anomalies = int(data["AnomalyLabel"].eq(-1).sum())
    normal = int(data["AnomalyLabel"].eq(1).sum())
    insufficient = int(data["AnomalyStatus"].eq("Insufficient data / not calculable").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anomalies", f"{total_anomalies:,}")
    c2.metric("Normal", f"{normal:,}")
    c3.metric("Insufficient Data", f"{insufficient:,}")
    c4.metric("Anomaly proportion", f"{total_anomalies / len(data):.1%}" if len(data) else "N/A")
    render_anomaly_distribution(data)
    st.info("Anomaly Score bukan probabilitas. Nilai lebih tinggi berarti observasi relatif lebih tidak biasa dalam distribusi yang dipelajari model.")
    st.markdown('<p class="section-title">Anomaly Results</p>', unsafe_allow_html=True)
    anomaly_cols = ["Ticker", "CompanyName", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "MScore", "AnomalyScore", "AnomalyLabel", "AnomalyStatus", "ScreeningPriority"]
    available = [c for c in anomaly_cols if c in data.columns]
    st.dataframe(data[available].sort_values("AnomalyScore", ascending=False), width="stretch", hide_index=True, column_config={"MScore": st.column_config.NumberColumn("M-Score", format="%.4f"), "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f")})


def render_risk_assessment(data: pd.DataFrame) -> None:
    st.markdown("### Risk Assessment")
    st.caption("Dua hasil screening ditampilkan berdampingan. Tidak ada composite risk score.")
    view = data.copy()
    view["ScreeningCategory"] = screening_category(view)
    columns = ["Ticker", "CompanyName", "FiscalYear", "RiskLabel", "AnomalyStatus", "ScreeningCategory", "MScore", "AnomalyScore"]
    available = [column for column in columns if column in view.columns]
    st.dataframe(view[available], width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)
    render_screening_matrix(view)


def render_company_analysis(data: pd.DataFrame) -> None:
    st.markdown("### Company Analysis")
    tickers = sorted(data["Ticker"].dropna().unique().tolist())
    if not tickers:
        st.info("Belum ada perusahaan dalam data.")
        return
    ticker = st.selectbox("Company", tickers)
    company = data[data["Ticker"].eq(ticker)].sort_values("FiscalYear")
    palette = chart_palette()
    left, right = st.columns(2)
    with left:
        fig = px.line(company, x="FiscalYear", y="MScore", markers=True)
        fig.add_hline(y=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"])
        st.plotly_chart(chart_layout(fig, "M-Score by year", palette), width="stretch")
    with right:
        fig = px.line(company, x="FiscalYear", y="AnomalyScore", markers=True)
        st.plotly_chart(chart_layout(fig, "Anomaly Score by year", palette), width="stretch")
    index_cols = ["Ticker", "CompanyName", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "MScore", "AnomalyScore"]
    st.dataframe(company[[column for column in index_cols if column in company.columns]], width="stretch", hide_index=True)


def render_upload_page(role: str) -> None:
    st.markdown("### Upload Financial Data")
    if not allowed(role, "upload"):
        st.error("Akses ditolak. User tidak dapat mengunggah data.")
        return
    st.caption("Format: XLSX, XLS, atau CSV. File divalidasi dan ditampilkan sebelum diproses.")
    uploaded = st.file_uploader("Financial statement workbook", type=["xlsx", "xls", "csv"])
    if uploaded is None:
        st.info("Pilih file untuk melihat preview. Database belum berubah.")
        return
    try:
        content = uploaded.getvalue()
        source = BytesIO(content)
        source.name = uploaded.name
        financial = read_upload(source)
        st.success(f"File valid. {len(financial):,} baris siap ditinjau.")
        st.dataframe(financial.head(100), width="stretch", hide_index=True)
        with st.form("confirm_upload"):
            confirmed = st.checkbox("Saya sudah memeriksa preview dan menyetujui pemrosesan file ini.")
            submitted = st.form_submit_button("Process and save", disabled=not confirmed)
        if submitted:
            analyzed = analyze(financial, AnalysisConfig())
            engine = create_mysql_engine()
            staged = 0
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                raw_source = BytesIO(content)
                raw_source.name = uploaded.name
                staged = load_staging(engine, read_workbook_long(raw_source))
            loaded = load_analysis(engine, analyzed)
            st.session_state.pop("financial_data", None)
            st.session_state.pop("analysis_data", None)
            st.success(f"Proses selesai: {staged:,} staging, {loaded:,} hasil analisis.")
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        st.error(f"File gagal divalidasi: {exc}")


def render_placeholder_page(title: str, message: str) -> None:
    st.markdown(f"### {title}")
    st.info(message)


def render_user_management(role: str) -> None:
    st.markdown("### User Management")
    if not allowed(role, "manage_accounts"):
        st.error("Akses ditolak. Hanya Administrator dapat mengelola akun.")
        return
    st.caption("Daftarkan akun baru beserta rolenya. Password disimpan sebagai hash PBKDF2.")
    with st.form("create_user"):
        username = st.text_input("Username")
        new_role = st.selectbox("Role", ["Stakeholder", "User", "Administrator"])
        password = st.text_input("Password sementara", type="password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if not username or not password:
            st.error("Username dan password wajib diisi.")
            return
        try:
            create_user(create_mysql_engine(), username, password, new_role)
            st.success(f"Akun {username} tersimpan sebagai {new_role}.")
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Akun gagal disimpan: {exc}")


def main() -> None:
    role = render_login()
    if role is None:
        return
    page = render_sidebar(role)
    if page == "Upload Financial Data":
        render_upload_page(role)
        return
    data = load_data()
    if data.empty:
        st.markdown("### Analytical Dashboard")
        st.info("Belum ada data. Upload workbook untuk memulai.")
        st.markdown('<div class="note-box">Hasil analisis adalah indikasi screening awal, bukan bukti fraud.</div>', unsafe_allow_html=True)
        return
    filtered = render_header(data, role, page)
    if filtered.empty:
        st.warning("Tidak ada observasi sesuai filter aktif. Tambah tahun atau hapus filter perusahaan.")
        return
    stored_analysis = {"MScore", "Status_178", "Status_222", "AnomalyScore", "AnomalyLabel"}.issubset(filtered.columns)
    analyzed = filtered if stored_analysis else analyze(filtered, AnalysisConfig())
    st.session_state["analysis_data"] = analyzed
    if not allowed(role, "analyze"):
        st.caption("View-only mode. Data dihitung tanpa mengubah sumber.")
    if page == "Overview":
        render_overview(analyzed)
    elif page == "Beneish M-Score":
        render_beneish_page(analyzed)
    elif page == "Anomaly Detection":
        render_anomaly_page(analyzed)
    elif page == "Risk Assessment":
        render_risk_assessment(analyzed)
    elif page == "Company Analysis":
        render_company_analysis(analyzed)
    elif page == "Analysis Results":
        render_companies_table(analyzed)
    elif page == "Upload History":
        render_placeholder_page("Upload History", "Upload history requires an Upload_History table. Database migration belum ditambahkan.")
    elif page == "Data Management":
        render_placeholder_page("Data Management", "Data management requires audit logging and explicit delete/update confirmation.")
    elif page == "User Management":
        render_user_management(role)
    st.markdown('<div class="note-box">Status screening membantu memprioritaskan review. Status apa pun tidak membuktikan fraud.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
