"""Page header: title, role chip, and the shared data filters."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_header(data: pd.DataFrame, role: str, page: str) -> pd.DataFrame:
    title, year_col, company_col, user_col = st.columns([2.1, 1.2, 1.5, 1.1])
    with title:
        st.markdown("### Manipulation Fraud Risk Dashboard")
        st.caption(page)
    with year_col:
        years = sorted(data["FiscalYear"].dropna().astype(int).unique().tolist())
        selected_years = st.multiselect("Year", years, default=years, placeholder="Filter by year")
    with user_col:
        st.markdown(f'<div class="user-chip"><span class="user-role">{role}</span><span class="user-scope">{"Full access" if role == "Administrator" else "Upload and export" if role == "Stakeholder" else "View only"}</span></div>', unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns([1.2, 1.2, 1.5])
    with filter_col1:
        subsectors = sorted(data["SubSector"].dropna().astype(str).unique().tolist()) if "SubSector" in data else []
        selected_subsectors = st.multiselect("Subsector", subsectors, placeholder="All subsectors")
    with filter_col2:
        statuses = sorted(data["RiskLabel"].dropna().astype(str).unique().tolist()) if "RiskLabel" in data else []
        selected_statuses = st.multiselect("Status", statuses, placeholder="All statuses")
    with company_col:
        tickers = sorted(data["Ticker"].dropna().unique().tolist())
        selected_tickers = st.multiselect("Company", tickers, placeholder="Filter by company code")
    filtered = data[data["FiscalYear"].isin(selected_years)] if selected_years else data.iloc[0:0]
    if selected_tickers:
        filtered = filtered[filtered["Ticker"].isin(selected_tickers)]
    if selected_subsectors:
        filtered = filtered[filtered["SubSector"].isin(selected_subsectors)]
    if selected_statuses:
        filtered = filtered[filtered["RiskLabel"].isin(selected_statuses)]
    active = []
    if selected_years:
        active.append(f"{len(selected_years)} year(s)")
    if selected_tickers:
        active.append(f"{len(selected_tickers)} company(s)")
    if selected_subsectors:
        active.append(f"{len(selected_subsectors)} subsector(s)")
    if selected_statuses:
        active.append(f"{len(selected_statuses)} status(es)")
    st.caption("Active filter: " + (", ".join(active) if active else "none"))
    return filtered
