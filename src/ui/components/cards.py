"""KPI metric cards."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.beneish import BASELINE_THRESHOLD


def render_kpis(data: pd.DataFrame) -> None:
    total_companies = data["Ticker"].nunique()
    total_obs = len(data)
    beneish_flags = int(data["RiskLabel"].eq("Potential earnings manipulation").sum())
    anomalies = int(data["AnomalyLabel"].eq(-1).sum())
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    cards = [
        (c1, "Total Companies", f"{total_companies:,}", "Entity scope", "neutral", "01"),
        (c2, "Observations", f"{total_obs:,}", "Company-year", "neutral", "02"),
        (c3, "Beneish Flags", f"{beneish_flags:,}", f"M-Score > {BASELINE_THRESHOLD}", "warning", "03"),
        (c4, "Anomalies", f"{anomalies:,}", "Isolation Forest", "danger", "04"),
    ]
    for column, title, value, detail, theme, icon in cards:
        with column:
            st.markdown(
                f'<div class="modern-card theme-{theme}"><div class="card-header"><span class="card-title">{title}</span><span class="card-icon-bubble">{icon}</span></div><div class="card-value">{value}</div><div class="card-footer"><span class="card-pill">{detail}</span></div></div>',
                unsafe_allow_html=True,
            )
