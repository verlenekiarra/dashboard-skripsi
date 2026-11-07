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
        return None, [], "CSV tidak memuat layout laporan."
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
        statement = st.selectbox("Laporan", statements, key="upload_report_statement")
    with pick_years:
        years = st.multiselect("Periode", all_years, default=all_years, key="upload_report_years")
    if not years:
        st.warning("Pilih minimal satu periode untuk menampilkan laporan.")
        return
    years = sorted(years)
    st.markdown('<p class="section-title">Laporan sesuai sumber</p>', unsafe_allow_html=True)
    render_report_matrix(report, statement, years)
    render_report_change(report, statement, years)
    render_report_trend(report, statement, years)


def _render_mapping(mapping, ticker: str) -> None:
    st.markdown('<p class="section-title">Pemetaan ke input Beneish</p>', unsafe_allow_html=True)
    rows = [
        {"Input model": column, "Akun sumber": source}
        for column, source in mapping.resolved.items()
    ]
    for column in mapping.unresolved:
        rows.append({"Input model": column, "Akun sumber": "tidak ditemukan"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    if mapping.unresolved:
        st.error(
            "Input berikut tidak ditemukan pada laporan: "
            + ", ".join(mapping.unresolved)
            + ". Beneish M-Score tidak dapat dihitung tanpa akun tersebut."
        )


def _render_analysis(analyzed: pd.DataFrame, training_size: int, population_rows: int) -> None:
    st.markdown('<p class="section-title">Hasil analisis</p>', unsafe_allow_html=True)
    columns = [
        "Ticker", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA",
        "MScore", "RiskLabel", "AnomalyScore", "AnomalyLabel", "AnomalyStatus", "ScreeningPriority",
    ]
    available = [c for c in columns if c in analyzed.columns]
    st.dataframe(
        analyzed[available], width="stretch", hide_index=True,
        column_config={
            "FiscalYear": st.column_config.NumberColumn("Periode", format="%d"),
            "MScore": st.column_config.NumberColumn("M-Score", format="%.4f"),
            "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f"),
            "RiskLabel": "M-Score Status",
            "AnomalyStatus": "Anomaly Status",
            "ScreeningPriority": "Screening",
        },
    )
    if population_rows:
        st.caption(
            f"Isolation Forest dilatih pada {training_size:,} observasi: "
            f"{population_rows:,} observasi tersimpan ditambah observasi dari file ini. "
            "Populasi pembanding diperlukan karena model tidak dapat menilai keanehan dari satu perusahaan saja."
        )
    else:
        st.warning(
            "Belum ada observasi tersimpan sebagai populasi pembanding, sehingga Isolation Forest "
            "hanya dilatih pada file ini. Label anomaly pada kondisi ini belum bermakna."
        )
    st.caption(
        "Tahun pertama setiap perusahaan berstatus insufficient data karena indeks Beneish "
        "membutuhkan tahun pembanding."
    )


def _save(analyzed: pd.DataFrame, content: bytes, filename: str, staging_frame: pd.DataFrame | None) -> None:
    engine = create_mysql_engine()
    staged = 0
    if staging_frame is not None:
        staged = load_staging(engine, staging_frame)
    loaded = load_analysis(engine, analyzed)
    st.session_state.pop("financial_data", None)
    st.session_state.pop("analysis_data", None)
    st.success(f"Proses selesai: {staged:,} staging, {loaded:,} hasil analisis.")


def _render_report_flow(content: bytes, filename: str, report: pd.DataFrame) -> None:
    st.success(
        f"Format laporan terdeteksi. {report['Statement'].nunique()} laporan, "
        f"{report['AccountName'].nunique():,} akun, "
        f"periode {report['FiscalYear'].min()}-{report['FiscalYear'].max()}."
    )
    ticker = st.text_input("Kode perusahaan", value=st.session_state.get(REPORT_TICKER, "TEST"), key="upload_report_code")
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
        "Saya sudah memeriksa laporan, pemetaan akun, dan hasil analisis.",
        key="confirm_report_upload",
    )
    with st.form("process_report_upload"):
        submitted = st.form_submit_button("Process and save", disabled=not confirmed)
    if submitted:
        try:
            _save(analyzed, content, filename, None)
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Penyimpanan gagal: {exc}")


def _render_tabular_flow(content: bytes, filename: str, financial: pd.DataFrame) -> None:
    st.success(f"File valid. {len(financial):,} baris siap ditinjau.")
    st.dataframe(financial.head(100), width="stretch", hide_index=True)
    confirmed = st.checkbox(
        "Saya sudah memeriksa preview dan menyetujui pemrosesan file ini.",
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
            st.error(f"Pemrosesan gagal: {exc}")


def render_upload_page(role: str) -> None:
    st.markdown("### Upload Financial Data")
    if not allowed(role, "upload"):
        st.error("Akses ditolak. User tidak dapat mengunggah data.")
        return
    st.caption("Format: XLSX, XLS, atau CSV. Laporan keuangan dan tabel data keduanya diterima; format dideteksi otomatis.")
    st.info("Upload minimal 2 tahun laporan untuk setiap perusahaan. Perhitungan indeks Beneish membutuhkan tahun pembanding.")
    uploaded = st.file_uploader("Financial statement workbook", type=["xlsx", "xls", "csv"])
    if uploaded is None:
        st.info("Pilih file untuk melihat preview. Database belum berubah.")
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
            st.caption("Workbook memuat beberapa sheet. Sheet pertama yang berformat laporan dipakai.")
        _render_report_flow(content, filename, report)
        return

    st.error("File tidak dikenali sebagai tabel data maupun laporan keuangan.")
    st.caption(f"Format tabel: {tabular_error}")
    if report_error:
        st.caption(f"Format laporan: {report_error}")
