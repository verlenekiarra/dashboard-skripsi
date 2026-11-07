"""Shared UI constants: roles, navigation, and table column config."""

from __future__ import annotations

import streamlit as st

ROLE_OPTIONS = ["Administrator", "Stakeholder", "User"]

NAV_BY_ROLE: dict[str, list[str]] = {
    "Administrator": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis", "Analysis Results", "Data Management", "Upload Financial Data", "User Management"],
    "Stakeholder": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis", "Upload Financial Data"],
    "User": ["Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis"],
}

RANK_COLUMN_CONFIG = {
    "RiskRank": st.column_config.NumberColumn("Rank", format="%d", help="Review order: screening tier, then M-Score, then anomaly score"),
    "MScore": st.column_config.NumberColumn("M-Score", format="%.4f"),
    "AnomalyScore": st.column_config.NumberColumn("Anomaly Score", format="%.4f"),
    "RiskLabel": "M-Score Status",
    "AnomalyStatus": "Anomaly Status",
    "ScreeningPriority": "Risk Status",
}
