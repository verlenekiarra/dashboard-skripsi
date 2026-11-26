from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.beneish import BASELINE_THRESHOLD
from src.ui.components.charts import render_mscore_distribution, render_mscore_trend


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
    st.info("The eight indices are signals in the Beneish model. Screening status is not proof of financial statement manipulation.")
    st.caption("DSRI: receivables relative to sales. GMI: gross margin. AQI: asset quality. SGI: sales growth. DEPI: depreciation. SGAI: selling and administrative expenses. LVGI: leverage. TATA: accruals relative to assets.")
    st.markdown('<p class="section-title">Detailed Indices</p>', unsafe_allow_html=True)
    index_cols = ["Ticker", "CompanyName", "FiscalYear", "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA", "MScore", "RiskLabel"]
    available = [c for c in index_cols if c in data.columns]
    st.dataframe(data[available].sort_values("MScore", ascending=False), width="stretch", hide_index=True)
