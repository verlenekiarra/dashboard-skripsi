from __future__ import annotations

import streamlit as st
import pandas as pd


def render_placeholder_page(title: str, message: str) -> None:
    st.markdown(f"### {title}")
    st.info(message)


def render_data_management(data: pd.DataFrame, role: str) -> None:
    st.markdown("### Data Management")
    if role != "Administrator":
        st.error("Akses ditolak. Hanya Administrator dapat mengelola data.")
        return

    st.caption("Monitoring data analisis dan pemeriksaan kualitas. Aksi delete/update belum diaktifkan.")
    companies = data["Ticker"].nunique() if "Ticker" in data else 0
    observations = len(data)
    years = data["FiscalYear"].nunique() if "FiscalYear" in data else 0
    missing_scores = int(data["MScore"].isna().sum()) if "MScore" in data else observations
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", f"{companies:,}")
    c2.metric("Observations", f"{observations:,}")
    c3.metric("Periods", f"{years:,}")
    c4.metric("Incomplete M-Score", f"{missing_scores:,}")

    quality = pd.DataFrame({
        "Quality check": [
            "Duplicate company-year",
            "Missing M-Score",
            "Missing Anomaly Label",
            "Missing Risk Label",
        ],
        "Rows": [
            int(data.duplicated(["Ticker", "FiscalYear"]).sum()) if {"Ticker", "FiscalYear"}.issubset(data.columns) else 0,
            int(data["MScore"].isna().sum()) if "MScore" in data.columns else observations,
            int(data["AnomalyLabel"].isna().sum()) if "AnomalyLabel" in data.columns else observations,
            int(data["RiskLabel"].isna().sum()) if "RiskLabel" in data.columns else observations,
        ],
    })
    st.markdown('<p class="section-title">Data quality</p>', unsafe_allow_html=True)
    st.dataframe(quality, width="stretch", hide_index=True)

    st.markdown('<p class="section-title">Company-year data</p>', unsafe_allow_html=True)
    columns = ["Ticker", "CompanyName", "Sector", "SubSector", "FiscalYear", "MScore", "RiskLabel", "AnomalyStatus"]
    available = [column for column in columns if column in data.columns]
    st.dataframe(data[available].sort_values([c for c in ["Ticker", "FiscalYear"] if c in available]), width="stretch", hide_index=True)
    st.info("Delete, update, audit log, dan reprocess belum diaktifkan karena memerlukan permission database dan mekanisme konfirmasi tambahan.")
