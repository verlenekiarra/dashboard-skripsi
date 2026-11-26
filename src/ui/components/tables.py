"""Dataframe tables shared across pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.config import RANK_COLUMN_CONFIG


def render_priority_table(data: pd.DataFrame) -> None:
    ranked = data.dropna(subset=["RiskRank"]).sort_values("RiskRank").head(5)
    st.markdown('<p class="section-title">Top 5 Company List by Risk</p>', unsafe_allow_html=True)
    if ranked.empty:
        st.info("No observations can be ranked. All rows have insufficient data.")
        return
    columns = ["RiskRank", "Ticker", "CompanyName", "FiscalYear", "MScore", "AnomalyScore", "ScreeningPriority"]
    st.dataframe(ranked[[c for c in columns if c in ranked.columns]], width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)
    st.caption("This is a review order, not a composite risk score or proof of fraud.")


def render_companies_table(data: pd.DataFrame) -> None:
    st.markdown('<p class="section-title">Companies List</p>', unsafe_allow_html=True)
    display_cols = ["Ticker", "CompanyName", "FiscalYear", "MScore", "RiskLabel", "AnomalyScore", "AnomalyStatus"]
    available = [c for c in display_cols if c in data.columns]
    # Alphabetical by ticker so this table reads as a directory, not a ranking.
    sort_keys = [c for c in ("Ticker", "FiscalYear") if c in available]
    table = data[available].sort_values(sort_keys) if sort_keys else data[available]
    st.dataframe(table, width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)
