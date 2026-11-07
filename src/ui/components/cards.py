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
    priority = int(data["ScreeningPriority"].eq("Priority screening").sum())
    avg_mscore = data["MScore"].mean()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Companies", f"{total_companies:,}")
    c2.metric("Observations", f"{total_obs:,}")
    c3.metric("Beneish Flags", f"{beneish_flags:,}", help=f"M-Score > {BASELINE_THRESHOLD}")
    c4.metric("Anomalies", f"{anomalies:,}", help="Isolation Forest label -1")
