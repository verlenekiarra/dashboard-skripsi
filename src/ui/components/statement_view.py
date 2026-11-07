"""Display pieces for a parsed statement report.

Pure rendering: these take an already-parsed report and draw it. Reading the
file, mapping it to model inputs, and saving belong to the page.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.statement_report import period_change, statement_matrix
from src.ui.components.charts import chart_layout
from src.ui.theme import chart_palette

ROW_KIND_LABELS = {
    "section": "Header seksi",
    "subheader": "Subheader",
    "account": "Akun",
    "subtotal": "Subtotal",
    "total": "Total",
}


def _indent(name: str, level: int) -> str:
    """Keep the source hierarchy readable once the Excel indent is gone."""
    return f"{'    ' * level}{name}"


def _with_labels(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    display["AccountName"] = [
        _indent(name, int(level))
        for name, level in zip(display["AccountName"], display["Level"])
    ]
    display["RowKind"] = display["RowKind"].map(ROW_KIND_LABELS).fillna(display["RowKind"])
    return display.drop(columns=["Level"])


def render_report_identity(report: pd.DataFrame, ticker: str) -> None:
    company = next((c for c in report["Company"].dropna().unique().tolist() if str(c).strip()), "")
    units = [u for u in report["Unit"].dropna().unique().tolist() if str(u).strip()]
    periods = [p for p in report["Period"].dropna().unique().tolist() if str(p).strip()]
    years = sorted(report["FiscalYear"].unique().tolist())
    st.markdown(f"#### {company}" if company else "#### Laporan keuangan")
    caption = [f"Kode: {ticker}"]
    if periods:
        caption.append(str(periods[0]))
    if units:
        caption.append(f"Disajikan dalam {units[0]}")
    caption.append(f"Periode {years[0]}-{years[-1]}")
    st.caption(" · ".join(caption))


def render_report_matrix(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    matrix = statement_matrix(report, statement, years)
    if matrix.empty:
        st.info("Tidak ada baris akun untuk laporan dan periode yang dipilih.")
        return
    display = _with_labels(matrix)
    column_config = {
        "AccountName": st.column_config.TextColumn("Akun", width="large"),
        "RowKind": st.column_config.TextColumn("Jenis baris"),
    }
    for year in years:
        column_config[str(year)] = st.column_config.NumberColumn(str(year), format="%.0f")
    st.dataframe(display, width="stretch", hide_index=True, column_config=column_config)
    st.caption("Sel kosong berarti akun tidak dilaporkan pada periode tersebut, berbeda dari nilai nol.")


def render_report_change(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    if len(years) < 2:
        st.info("Pilih minimal dua periode untuk membandingkan perubahan antarperiode.")
        return
    st.markdown('<p class="section-title">Perubahan antarperiode</p>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        base_year = st.selectbox("Periode dasar", years, index=len(years) - 2, key=f"base_{statement}")
    with right:
        later = [year for year in years if year != base_year]
        compare_year = st.selectbox("Periode pembanding", later, index=len(later) - 1, key=f"compare_{statement}")

    change = period_change(report, statement, base_year, compare_year)
    if change.empty:
        st.info("Tidak ada data untuk pasangan periode tersebut.")
        return
    st.dataframe(
        _with_labels(change), width="stretch", hide_index=True,
        column_config={
            "AccountName": st.column_config.TextColumn("Akun", width="large"),
            "RowKind": st.column_config.TextColumn("Jenis baris"),
            str(base_year): st.column_config.NumberColumn(str(base_year), format="%.0f"),
            str(compare_year): st.column_config.NumberColumn(str(compare_year), format="%.0f"),
            "Change": st.column_config.NumberColumn("Perubahan nominal", format="%.0f"),
            "ChangePercent": st.column_config.NumberColumn("Perubahan %", format="%.2f"),
        },
    )
    st.caption("Perubahan persentase dikosongkan bila periode dasar bernilai nol atau tidak dilaporkan.")


def render_report_trend(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    st.markdown('<p class="section-title">Tren akun</p>', unsafe_allow_html=True)
    subset = report[report["Statement"].eq(statement) & report["FiscalYear"].isin(years)]
    valued = subset.dropna(subset=["Value"])
    accounts = (
        valued[["RowOrder", "AccountName"]]
        .drop_duplicates("RowOrder")
        .sort_values("RowOrder")["AccountName"]
        .tolist()
    )
    if not accounts:
        st.info("Belum ada akun bernilai yang dapat ditampilkan sebagai tren.")
        return
    account = st.selectbox("Akun", accounts, key=f"trend_{statement}")
    series = valued[valued["AccountName"].eq(account)].sort_values("FiscalYear")
    if series.empty:
        st.info("Akun ini tidak memiliki nilai pada periode yang dipilih.")
        return
    palette = chart_palette()
    fig = px.line(series, x="FiscalYear", y="Value", markers=True)
    st.plotly_chart(chart_layout(fig, account, palette), width="stretch")
    history = series[["FiscalYear", "Value", "RowKind"]].copy()
    history["RowKind"] = history["RowKind"].map(ROW_KIND_LABELS).fillna(history["RowKind"])
    st.dataframe(
        history, width="stretch", hide_index=True,
        column_config={
            "FiscalYear": st.column_config.NumberColumn("Periode", format="%d"),
            "Value": st.column_config.NumberColumn("Nilai", format="%.0f"),
            "RowKind": st.column_config.TextColumn("Jenis baris"),
        },
    )
