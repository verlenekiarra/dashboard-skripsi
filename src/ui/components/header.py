"""Page header: title, role chip, and the shared data filters."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st


def render_header(data: pd.DataFrame, role: str, page: str) -> pd.DataFrame:
    band = st.empty()
    year_col, company_col, filter_col1, filter_col2 = st.columns([1.3, 1.3, 1.1, 1.1])
    with year_col:
        years = sorted(data["FiscalYear"].dropna().astype(int).unique().tolist())
        selected_years = st.multiselect("Year", years, default=years, placeholder="Filter by year", key="header_year_filter")
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
    if selected_tickers:
        active.append(f"{len(selected_tickers)} company")
    if selected_subsectors:
        active.append(f"{len(selected_subsectors)} subsector")
    if selected_statuses:
        active.append(f"{len(selected_statuses)} status")
    scope = {"Administrator": "Full access", "Stakeholder": "Upload and export"}.get(role, "View only")
    period = f"{min(selected_years)}–{max(selected_years)}" if selected_years else "No year"
    chips = "".join(f'<span class="hb-chip">{escape(item)}</span>' for item in active) or '<span class="hb-chip hb-chip-muted">No extra filters</span>'
    band.markdown(
        f'<div class="header-band"><div class="hb-main"><div class="hb-kicker">{escape(role)} · {scope}</div>'
        f'<h2 class="hb-title">{escape(page)}</h2><div class="hb-chips">{chips}</div></div>'
        f'<div class="hb-stats"><div class="hb-stat hb-blue"><span>Period</span><strong>{period}</strong></div>'
        f'<div class="hb-stat hb-teal"><span>Companies</span><strong>{filtered["Ticker"].nunique():,}</strong></div>'
        f'<div class="hb-stat hb-violet"><span>Observations</span><strong>{len(filtered):,}</strong></div></div></div>',
        unsafe_allow_html=True,
    )
    return filtered
