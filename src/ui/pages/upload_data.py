from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.analytics.beneish import AnalysisConfig, analyze
from src.analytics.population_scoring import analyze_against_population
from src.auth.permissions import allowed
from src.data.database import create_mysql_engine
from src.data.io import read_upload, read_workbook_long
from src.data.repository import load_analysis, load_staging, read_analysis
from src.data.statement_mapping import map_report_to_financials
from src.data.statement_report import read_statement_report
from src.ui.components.statement_view import (
    render_report_change,
    render_report_identity,
    render_report_matrix,
    render_report_trend,
)

REPORT_KEY = "upload_report_data"
REPORT_TICKER = "upload_report_ticker"
REPORT_NAME = "upload_report_filename"


def _sheet_names(content: bytes, filename: str) -> list[str]:
    buffer = BytesIO(content)
    buffer.name = filename
    return pd.ExcelFile(buffer).sheet_names


def _read_tabular(content: bytes, filename: str) -> pd.DataFrame:
    source = BytesIO(content)
    source.name = filename
    return read_upload(source)


def _try_report(content: bytes, filename: str) -> tuple[pd.DataFrame | None, list[str], str]:
    """Attempt every sheet as a printed report. Returns (data, sheets, error)."""
    if filename.lower().endswith(".csv"):
        return None, [], "CSV does not contain a report layout."
    try:
        sheets = _sheet_names(content, filename)
    except (OSError, ValueError) as exc:
        return None, [], str(exc)
    last_error = ""
    for sheet in sheets:
        try:
            buffer = BytesIO(content)
            buffer.name = filename
            return read_statement_report(buffer, sheet_name=sheet), sheets, ""
        except (OSError, ValueError, KeyError) as exc:
            last_error = str(exc)
    return None, sheets, last_error


def _render_report_review(report: pd.DataFrame, ticker: str) -> None:
    render_report_identity(report, ticker)
    statements = report["Statement"].drop_duplicates().tolist()
    all_years = sorted(report["FiscalYear"].unique().tolist())
    pick_statement, pick_years = st.columns([1.2, 1.8])
    with pick_statement:
        statement = st.selectbox("Statement", statements, key="upload_report_statement")
    with pick_years:
        years = st.multiselect("Period", all_years, default=all_years, key="upload_report_years")
    if not years:
        st.warning("Select at least one period to display the report.")
        return
    years = sorted(years)
    st.markdown('<p class="section-title">Source report</p>', unsafe_allow_html=True)
    render_report_matrix(report, statement, years)
    render_report_change(report, statement, years)
    render_report_trend(report, statement, years)


def _render_mapping(mapping, ticker: str) -> None:
    st.markdown('<p class="section-title">Beneish input mapping</p>', unsafe_allow_html=True)
    rows = [
        {"Model input": column, "Source account": source}
        for column, source in mapping.resolved.items()
    ]
    for column in mapping.unresolved:
        rows.append({"Model input": column, "Source account": "Not found"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    if mapping.unresolved:
        st.error(
            "The following inputs were not found in the report: "
            + ", ".join(mapping.unresolved)
            + ". Beneish M-Score cannot be calculated without these accounts."
        )


def _render_analysis(analyzed: pd.DataFrame, training_size: int, population_rows: int) -> None:
    st.markdown('<p class="section-title">Analysis results</p>', unsafe_allow_html=True)
    columns = [
        "Ticker", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA",
        "MScore", "RiskLabel", "AnomalyScore", "AnomalyLabel", "AnomalyStatus", "ScreeningPriority",
    ]
    available = [c for c in columns if c in analyzed.columns]
    st.dataframe(
        analyzed[available], width="stretch", hide_index=True,
        column_config={
            "FiscalYear": st.column_config.NumberColumn("Period", format="%d"),
            "MScore": st.column_config.NumberColumn("M-Score", format="%.4f"),
            "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f"),
            "RiskLabel": "M-Score Status",
            "AnomalyStatus": "Anomaly Status",
            "ScreeningPriority": "Screening",
        },
    )
    if population_rows:
        st.caption(
            f"Isolation Forest was trained on {training_size:,} observations: "
            f"{population_rows:,} stored observations plus observations from this file. "
            "A comparison population is required because the model cannot assess unusualness from one company alone."
        )
    else:
        st.warning(
            "No stored observations are available as a comparison population, so Isolation Forest "
            "was trained only on this file. Anomaly labels are not meaningful in this condition."
        )
    st.caption(
        "The first year for each company has insufficient data because Beneish indices "
        "require a comparison year."
    )


def _save(analyzed: pd.DataFrame, content: bytes, filename: str, staging_frame: pd.DataFrame | None) -> None:
    engine = create_mysql_engine()
    staged = 0
    if staging_frame is not None:
        staged = load_staging(engine, staging_frame)
    loaded = load_analysis(engine, analyzed)
    st.session_state.pop("financial_data", None)
    st.session_state.pop("analysis_data", None)
    st.success(f"Process complete: {staged:,} staging records, {loaded:,} analysis results.")


def _render_report_flow(content: bytes, filename: str, report: pd.DataFrame) -> None:
    st.success(
        f"Report format detected. {report['Statement'].nunique()} statements, "
        f"{report['AccountName'].nunique():,} accounts, "
        f"period {report['FiscalYear'].min()}-{report['FiscalYear'].max()}."
    )
    ticker = st.text_input("Company ticker", value=st.session_state.get(REPORT_TICKER, "TEST"), key="upload_report_code")
    ticker = ticker.strip() or "TEST"
    st.session_state[REPORT_TICKER] = ticker

    _render_report_review(report, ticker)

    mapping = map_report_to_financials(report, ticker=ticker)
    _render_mapping(mapping, ticker)
    if not mapping.is_complete:
        return

    try:
        population = read_analysis(create_mysql_engine())
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        population = pd.DataFrame()
    population_rows = 0 if population.empty else len(population)
    analyzed, training_size = analyze_against_population(mapping.frame, population)
    _render_analysis(analyzed, training_size, population_rows)

    confirmed = st.checkbox(
        "I have reviewed the report, account mapping, and analysis results.",
        key="confirm_report_upload",
    )
    with st.form("process_report_upload"):
        submitted = st.form_submit_button("Process and save", disabled=not confirmed)
    if submitted:
        try:
            _save(analyzed, content, filename, None)
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Save failed: {exc}")


def _render_tabular_flow(content: bytes, filename: str, financial: pd.DataFrame) -> None:
    st.success(f"Valid file. {len(financial):,} rows are ready for review.")
    st.dataframe(financial.head(100), width="stretch", hide_index=True)
    confirmed = st.checkbox(
        "I have reviewed the preview and approve processing this file.",
        key="confirm_table_upload",
    )
    with st.form("process_table_upload"):
        submitted = st.form_submit_button("Process and save", disabled=not confirmed)
    if submitted:
        try:
            analyzed = analyze(financial, AnalysisConfig())
            staging_frame = None
            if filename.lower().endswith((".xlsx", ".xls")):
                raw_source = BytesIO(content)
                raw_source.name = filename
                staging_frame = read_workbook_long(raw_source)
            _save(analyzed, content, filename, staging_frame)
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Processing failed: {exc}")


def render_upload_page(role: str) -> None:
    st.markdown("### Upload Financial Data")
    if not allowed(role, "upload"):
        st.error("Access denied. Users cannot upload data.")
        return
    st.caption("Formats: XLSX, XLS, or CSV. Financial statements and tabular data are accepted; format is detected automatically.")
    st.info("Upload at least 2 reporting years for each company. Beneish index calculations require a comparison year.")
    uploaded = st.file_uploader("Financial statement workbook", type=["xlsx", "xls", "csv"])
    if uploaded is None:
        st.info("Choose a file to view its preview. The database has not changed.")
        return

    content = uploaded.getvalue()
    filename = uploaded.name

    tabular: pd.DataFrame | None = None
    tabular_error = ""
    try:
        tabular = _read_tabular(content, filename)
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        tabular_error = str(exc)

    if tabular is not None:
        _render_tabular_flow(content, filename, tabular)
        return

    report, sheets, report_error = _try_report(content, filename)
    if report is not None:
        if len(sheets) > 1:
            st.caption("The workbook contains multiple sheets. The first sheet with a valid report format will be used.")
        _render_report_flow(content, filename, report)
        return

    st.error("The file was not recognized as tabular data or a financial report.")
    st.caption(f"Tabular format: {tabular_error}")
    if report_error:
        st.caption(f"Report format: {report_error}")
