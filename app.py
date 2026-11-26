from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Financial Risk Analytics", layout="wide", initial_sidebar_state="expanded")

from src.analytics.beneish import AnalysisConfig, analyze
from src.auth.permissions import allowed
from src.ui.auth_view import render_login
from src.ui.components.header import render_header
from src.ui.components.sidebar import render_sidebar
from src.ui.components.tables import render_companies_table
from src.ui.data_loader import load_data
from src.ui.pages.anomaly_detection import render_anomaly_page
from src.ui.pages.beneish import render_beneish_page
from src.ui.pages.company_analysis import render_company_analysis
from src.ui.pages.data_management import render_data_management
from src.ui.pages.overview import render_overview
from src.ui.pages.placeholder import render_placeholder_page
from src.ui.pages.risk_assessment import render_risk_assessment
from src.ui.pages.upload_data import render_upload_page
from src.ui.pages.user_management import render_user_management
from src.ui.theme import active_theme, apply_theme

ACTIVE_THEME = active_theme()
apply_theme(ACTIVE_THEME)


def main() -> None:
    role = render_login()
    if role is None:
        return
    page = render_sidebar(role)
    if page == "Upload Financial Data":
        render_upload_page(role)
        return

    data = load_data()
    if data.empty:
        st.markdown("### Manipulation Fraud Risk Dashboard")
        st.info("No data is available. Upload a workbook to begin.")
        st.markdown('<div class="note-box">Screening results support review. No status proves fraud or financial statement manipulation.</div>', unsafe_allow_html=True)
        return
    filtered = data if page in {"Data Management", "User Management"} else render_header(data, role, page)
    if filtered.empty:
        st.warning("No observations match the active filters. Add a year or clear the company filter.")
        return
    stored_analysis = {"MScore", "Status_178", "Status_222", "AnomalyScore", "AnomalyLabel"}.issubset(filtered.columns)
    analyzed = filtered if stored_analysis else analyze(filtered, AnalysisConfig())
    st.session_state["analysis_data"] = analyzed
    if not allowed(role, "analyze"):
        st.caption("View-only mode. Data is calculated without changing the source.")
    if page == "Overview":
        render_overview(analyzed)
    elif page == "Beneish M-Score":
        render_beneish_page(analyzed)
    elif page == "Anomaly Detection":
        render_anomaly_page(analyzed)
    elif page == "Risk Assessment":
        render_risk_assessment(analyzed)
    elif page == "Company Analysis":
        render_company_analysis(analyzed)
    elif page == "Analysis Results":
        render_companies_table(analyzed)
    elif page == "Upload History":
        render_placeholder_page("Upload History", "Upload history requires an Upload_History table. Database migration belum ditambahkan.")
    elif page == "Data Management":
        render_data_management(analyzed, role)
    elif page == "User Management":
        render_user_management(role)
    st.markdown('<div class="note-box">Screening results help prioritize review. No status proves fraud or financial statement manipulation.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
