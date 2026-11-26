from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.cards import render_kpis
from src.ui.components.charts import render_anomaly_distribution, render_mscore_trend, render_scatter, render_screening_matrix
from src.ui.components.tables import render_companies_table, render_priority_table


def render_overview(data: pd.DataFrame) -> None:
    render_kpis(data)
    st.markdown('<div class="overview-chart-gap"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        render_mscore_trend(data)
    with col2:
        render_anomaly_distribution(data)
    st.markdown('<p class="section-title">Cross-method signal</p>', unsafe_allow_html=True)
    render_scatter(data)
    st.markdown('<p class="section-title">Independent screening comparison</p>', unsafe_allow_html=True)
    render_screening_matrix(data)
    col3, col4 = st.columns([1.5, 1])
    with col3:
        render_companies_table(data)
    with col4:
        render_priority_table(data)
