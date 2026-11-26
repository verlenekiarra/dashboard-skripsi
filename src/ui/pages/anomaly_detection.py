from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import render_anomaly_distribution


def render_anomaly_page(data: pd.DataFrame) -> None:
    st.markdown("### Anomaly Detection")
    st.caption("Isolation Forest identifies unusual financial patterns. A higher score indicates a relatively less common observation.")
    total_anomalies = int(data["AnomalyLabel"].eq(-1).sum())
    normal = int(data["AnomalyLabel"].eq(1).sum())
    insufficient = int(data["AnomalyStatus"].eq("Insufficient data / not calculable").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anomalies", f"{total_anomalies:,}")
    c2.metric("Normal", f"{normal:,}")
    c3.metric("Insufficient Data", f"{insufficient:,}")
    c4.metric("Anomaly proportion", f"{total_anomalies / len(data):.1%}" if len(data) else "N/A")
    render_anomaly_distribution(data)
    st.info("Anomaly Score is not a probability. A higher value indicates a relatively less common observation in the learned distribution.")
    st.markdown('<p class="section-title">Anomaly Results</p>', unsafe_allow_html=True)
    anomaly_cols = ["Ticker", "CompanyName", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "MScore", "AnomalyScore", "AnomalyLabel", "AnomalyStatus", "ScreeningPriority"]
    available = [c for c in anomaly_cols if c in data.columns]
    st.dataframe(data[available].sort_values("AnomalyScore", ascending=False), width="stretch", hide_index=True, column_config={"MScore": st.column_config.NumberColumn("M-Score", format="%.4f"), "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f")})
