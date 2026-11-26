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
    "section": "Section header",
    "subheader": "Subheader",
    "account": "Account",
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
    st.markdown(f"#### {company}" if company else "#### Financial statement")
    caption = [f"Ticker: {ticker}"]
    if periods:
        caption.append(str(periods[0]))
    if units:
        caption.append(f"Disajikan dalam {units[0]}")
    caption.append(f"Period {years[0]}-{years[-1]}")
    st.caption(" · ".join(caption))


def render_report_matrix(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    matrix = statement_matrix(report, statement, years)
    if matrix.empty:
        st.info("No account rows are available for the selected statement and periods.")
        return
    display = _with_labels(matrix)
    column_config = {
        "AccountName": st.column_config.TextColumn("Account", width="large"),
        "RowKind": st.column_config.TextColumn("Row type"),
    }
    for year in years:
        column_config[str(year)] = st.column_config.NumberColumn(str(year), format="%.0f")
    st.dataframe(display, width="stretch", hide_index=True, column_config=column_config)
    st.caption("A blank cell means the account was not reported for that period, not that its value was zero.")


def render_report_change(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    if len(years) < 2:
        st.info("Select at least two periods to compare changes between periods.")
        return
    st.markdown('<p class="section-title">Period changes</p>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        base_year = st.selectbox("Base period", years, index=len(years) - 2, key=f"base_{statement}")
    with right:
        later = [year for year in years if year != base_year]
        compare_year = st.selectbox("Comparison period", later, index=len(later) - 1, key=f"compare_{statement}")

    change = period_change(report, statement, base_year, compare_year)
    if change.empty:
        st.info("No data is available for this period pair.")
        return
    st.dataframe(
        _with_labels(change), width="stretch", hide_index=True,
        column_config={
            "AccountName": st.column_config.TextColumn("Account", width="large"),
            "RowKind": st.column_config.TextColumn("Row type"),
            str(base_year): st.column_config.NumberColumn(str(base_year), format="%.0f"),
            str(compare_year): st.column_config.NumberColumn(str(compare_year), format="%.0f"),
            "Change": st.column_config.NumberColumn("Nominal change", format="%.0f"),
            "ChangePercent": st.column_config.NumberColumn("Change %", format="%.2f"),
        },
    )
    st.caption("Percentage change is blank when the base period is zero or was not reported.")


def render_report_trend(report: pd.DataFrame, statement: str, years: list[int]) -> None:
    st.markdown('<p class="section-title">Account trend</p>', unsafe_allow_html=True)
    subset = report[report["Statement"].eq(statement) & report["FiscalYear"].isin(years)]
    valued = subset.dropna(subset=["Value"])
    accounts = (
        valued[["RowOrder", "AccountName"]]
        .drop_duplicates("RowOrder")
        .sort_values("RowOrder")["AccountName"]
        .tolist()
    )
    if not accounts:
        st.info("No valued accounts are available for a trend view.")
        return
    account = st.selectbox("Account", accounts, key=f"trend_{statement}")
    series = valued[valued["AccountName"].eq(account)].sort_values("FiscalYear")
    if series.empty:
        st.info("This account has no values for the selected periods.")
        return
    palette = chart_palette()
    fig = px.line(series, x="FiscalYear", y="Value", markers=True)
    st.plotly_chart(chart_layout(fig, account, palette), width="stretch", config={"displaylogo": False, "responsive": True})
    history = series[["FiscalYear", "Value", "RowKind"]].copy()
    history["RowKind"] = history["RowKind"].map(ROW_KIND_LABELS).fillna(history["RowKind"])
    st.dataframe(
        history, width="stretch", hide_index=True,
        column_config={
            "FiscalYear": st.column_config.NumberColumn("Period", format="%d"),
            "Value": st.column_config.NumberColumn("Value", format="%.0f"),
            "RowKind": st.column_config.TextColumn("Row type"),
        },
    )
