"""Sidebar: role brand, sign out, navigation, and export buttons."""

from __future__ import annotations

import streamlit as st

from src.auth.permissions import allowed
from src.data.io import export_csv, export_excel
from src.ui.config import NAV_BY_ROLE


def render_sidebar(role: str) -> str:
    with st.sidebar:
        st.markdown(f'<div class="sidebar-brand">{role}</div>', unsafe_allow_html=True)
        if st.button("Sign out", width="stretch"):
            st.session_state.pop("authenticated_role", None)
            st.rerun()
        st.markdown("---")
        pages = NAV_BY_ROLE.get(role, NAV_BY_ROLE["User"])
        current = st.session_state.get("active_page", pages[0])
        if current not in pages:
            current = pages[0]
        st.markdown('<div class="sidebar-label">Navigation</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-control">', unsafe_allow_html=True)
        page = st.segmented_control("Navigation", pages, default=current, label_visibility="collapsed", key="sidebar_navigation")
        st.markdown('</div>', unsafe_allow_html=True)
        page = page or current
        st.session_state["active_page"] = page
        if allowed(role, "export") and "analysis_data" in st.session_state:
            st.markdown('<p class="section-title">Export</p>', unsafe_allow_html=True)
            export_frame = st.session_state["analysis_data"]
            st.download_button("CSV", export_csv(export_frame), "risk_analysis.csv", "text/csv", width="stretch")
            st.download_button("Excel", export_excel(export_frame), "risk_analysis.xlsx", width="stretch")
    return page
