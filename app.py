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
from src.auth.permissions import allowed
from src.data.database import create_mysql_engine
from src.data.io import export_csv, export_excel, read_upload, read_workbook_long
from src.data.repository import load_analysis, load_staging, read_analysis

st.set_page_config(page_title="Financial Risk Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
    --bg: #d8eafc;
    --surface: #f4faff;
    --surface-alt: #e7f2fe;
    --border: #a9cdee;
    --border-strong: #5d87b4;
    --text: #0b2340;
    --text-muted: #415d85;
    --primary: #1f5fd0;
    --accent-soft: #bde0fe;
    --btn-bg: #1f5fd0;
    --btn-fg: #ffffff;
    --btn-hover: #17499f;
    --tier-1: #5b34a8;
    --tier-2: #9a5a00;
    --tier-3: #1f5fd0;
    --tier-4: #0e7068;
    --tier-5: #51658a;
    --radius: 14px;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #07182c;
        --surface: #102542;
        --surface-alt: #15304f;
        --border: #27486f;
        --border-strong: #6b93c4;
        --text: #e8f2fd;
        --text-muted: #a9c4e2;
        --primary: #7db6f5;
        --accent-soft: #1b3a5e;
        --btn-bg: #7db6f5;
        --btn-fg: #07182c;
        --btn-hover: #a4cdf9;
        --tier-1: #c3a6f2;
        --tier-2: #e8b571;
        --tier-3: #7db6f5;
        --tier-4: #5fd3c4;
        --tier-5: #9fb4d4;
    }
}
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"] { right: .75rem; top: .35rem; }
[data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1400px; padding: 3rem 2rem 3rem; }
section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }
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
.user-chip { display: flex; flex-direction: column; align-items: flex-end; gap: .15rem; padding: .5rem .75rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
.user-role { font-size: .85rem; font-weight: 600; color: var(--text); }
.user-scope { font-size: .7rem; color: var(--text-muted); }
div[data-testid="stForm"] { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }
.stButton>button { background: var(--btn-bg); color: var(--btn-fg); border: none; border-radius: 8px; font-weight: 500; padding: .5rem 1.25rem; }
.stButton>button:hover { background: var(--btn-hover); color: var(--btn-fg); }
.stDownloadButton>button { background: var(--surface); color: var(--text); border: 1px solid var(--border); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput input, [data-baseweb="input"], [data-baseweb="select"]>div { border-color: var(--border-strong) !important; border-radius: 8px; }
.stDownloadButton>button { border-color: var(--border-strong); }
:focus-visible { outline: 2px solid var(--primary) !important; outline-offset: 2px !important; }
</style>
""", unsafe_allow_html=True)


CHART_LIGHT = {
    "surface": "#f4faff", "text": "#415d85", "title": "#0b2340",
    "grid": "#c4dcf5", "zero": "#a9cdee", "line": "#1f5fd0",
    "baseline": "#5b34a8", "sensitivity": "#9a5a00",
    "tiers": {
        "Priority screening": "#5b34a8", "Beneish flag": "#9a5a00",
        "Anomaly flag": "#1f5fd0", "Low priority": "#0e7068",
        "Insufficient data / not calculable": "#51658a",
    },
}
CHART_DARK = {
    "surface": "#102542", "text": "#a9c4e2", "title": "#e8f2fd",
    "grid": "#27486f", "zero": "#335a86", "line": "#7db6f5",
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
    "Administrator": ["Overview", "Beneish M-Score", "Anomaly Detection", "Manage Dashboard", "User Management"],
    "Stakeholder": ["Overview", "Beneish M-Score", "Anomaly Detection", "Manage Dashboard"],
    "User": ["Overview", "Beneish M-Score", "Anomaly Detection"],
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
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("Financial Risk Analytics")
        st.caption("Dashboard analitik risiko manipulasi laporan keuangan")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width="stretch")
        if submitted:
            from src.auth.permissions import authenticate
            role = authenticate(username, password)
            if role:
                st.session_state["authenticated_role"] = role
                st.rerun()
            st.error("Username atau password tidak valid.")
        if not os.getenv("APP_USERS_JSON"):
            st.markdown('<div class="note-box">APP_USERS_JSON belum dikonfigurasi. Lihat dokumentasi untuk setup login.</div>', unsafe_allow_html=True)
    return None


def render_sidebar(role: str) -> str:
    with st.sidebar:
        st.markdown(f"### {role}")
        if st.button("Sign out", width="stretch"):
            st.session_state.pop("authenticated_role", None)
            st.rerun()
        st.markdown("---")
        page = st.radio("Navigation", NAV_BY_ROLE.get(role, NAV_BY_ROLE["User"]), label_visibility="collapsed")
        st.markdown("---")
        if allowed(role, "upload"):
            st.markdown('<p class="section-title">Upload Data</p>', unsafe_allow_html=True)
            uploaded = st.file_uploader("Upload workbook", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
            if uploaded is not None:
                try:
                    content = uploaded.getvalue()
                    analytic_source = BytesIO(content)
                    analytic_source.name = uploaded.name
                    financial = read_upload(analytic_source)
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
                    st.success(f"ETL selesai: {staged:,} staging, {loaded:,} hasil analisis.")
                    st.rerun()
                except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
                    st.error(str(exc))
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
    with company_col:
        tickers = sorted(data["Ticker"].dropna().unique().tolist())
        selected_tickers = st.multiselect("Company", tickers, placeholder="Filter by company code")
    with user_col:
        st.markdown(f'<div class="user-chip"><span class="user-role">{role}</span><span class="user-scope">{"Full access" if role == "Administrator" else "Upload and export" if role == "Stakeholder" else "View only"}</span></div>', unsafe_allow_html=True)
    filtered = data[data["FiscalYear"].isin(selected_years)] if selected_years else data.iloc[0:0]
    if selected_tickers:
        filtered = filtered[filtered["Ticker"].isin(selected_tickers)]
    active = []
    if selected_years:
        active.append(f"{len(selected_years)} year(s)")
    if selected_tickers:
        active.append(f"{len(selected_tickers)} company(s)")
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
    c2.metric("Beneish M-Score", f"{avg_mscore:.2f}" if pd.notna(avg_mscore) else "N/A")
    c3.metric("Beneish Flags", f"{beneish_flags:,}", help=f"M-Score > {BASELINE_THRESHOLD}")
    c4.metric("Priority Screening", f"{priority:,}", help=f"Flagged by both methods. Anomalies: {anomalies:,}")


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
        render_scatter(data)
    col3, col4 = st.columns([1.5, 1])
    with col3:
        render_companies_table(data)
    with col4:
        render_priority_table(data)


def render_beneish_page(data: pd.DataFrame) -> None:
    st.markdown("### Beneish M-Score Analysis")
    st.caption(f"Threshold: M-Score > {BASELINE_THRESHOLD} indicates potential earnings manipulation")
    render_kpis(data)
    col1, col2 = st.columns(2)
    with col1:
        render_mscore_trend(data)
    with col2:
        render_scatter(data)
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
    c1, c2, c3 = st.columns(3)
    c1.metric("Anomalies", f"{total_anomalies:,}")
    c2.metric("Normal", f"{normal:,}")
    c3.metric("Insufficient Data", f"{insufficient:,}")
    render_scatter(data)
    st.markdown('<p class="section-title">Anomaly Results</p>', unsafe_allow_html=True)
    anomaly_cols = ["Ticker", "CompanyName", "FiscalYear", "MScore", "AnomalyScore", "AnomalyLabel", "AnomalyStatus", "ScreeningPriority"]
    available = [c for c in anomaly_cols if c in data.columns]
    st.dataframe(data[available].sort_values("AnomalyScore", ascending=False), width="stretch", hide_index=True, column_config={"MScore": st.column_config.NumberColumn("M-Score", format="%.4f"), "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f")})


def render_manage_page(role: str) -> None:
    st.markdown("### Manage Dashboard")
    if role == "Administrator":
        st.info("Administrator dapat mengelola data, ETL, analitik, akun, dan sistem.")
    elif role == "Stakeholder":
        st.info("Stakeholder dapat upload data, menjalankan analisis, dan export hasil.")
    else:
        st.info("User memiliki akses view-only.")


def render_user_management(role: str) -> None:
    st.markdown("### User Management")
    if not allowed(role, "manage_accounts"):
        st.error("Akses ditolak. Hanya Administrator dapat mengelola akun.")
        return
    st.caption("Daftarkan akun baru beserta rolenya. Password disimpan sebagai hash PBKDF2.")
    with st.form("create_user"):
        email = st.text_input("Email")
        new_role = st.selectbox("Role", ["Stakeholder", "User", "Administrator"])
        password = st.text_input("Password sementara", type="password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if not email or not password:
            st.error("Email dan password wajib diisi.")
            return
        from src.auth.permissions import hash_password
        st.success(f"Hash dibuat untuk {email} sebagai {new_role}.")
        st.code(f'"{email}": {{"password_hash": "{hash_password(password)}", "role": "{new_role}"}}', language="json")
        st.markdown('<div class="note-box">Tabel <code>users</code> di MySQL belum ada, jadi akun belum tersimpan permanen. Tambahkan entri di atas ke APP_USERS_JSON, atau setujui pembuatan tabel <code>users</code> agar pendaftaran langsung tersimpan ke database.</div>', unsafe_allow_html=True)


def main() -> None:
    role = render_login()
    if role is None:
        return
    page = render_sidebar(role)
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
    elif page == "User Management":
        render_user_management(role)
    else:
        render_manage_page(role)
    st.markdown('<div class="note-box">Status screening membantu memprioritaskan review. Status apa pun tidak membuktikan fraud.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
