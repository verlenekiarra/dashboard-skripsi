from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.beneish import BASELINE_THRESHOLD
from src.ui.components.charts import chart_layout
from src.ui.theme import chart_palette


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
