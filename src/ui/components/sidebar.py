"""Sidebar: brand, grouped role-aware navigation, exports, and sign out."""

from __future__ import annotations

import re

import streamlit as st

from src.auth.permissions import allowed
from src.data.io import export_csv, export_excel
from src.ui.config import NAV_BY_ROLE

DASHBOARD_PAGES = ("Overview", "Beneish M-Score", "Anomaly Detection", "Risk Assessment", "Company Analysis")
NAV_ICONS = {
    "Analysis Results": ":material/table_chart:",
    "Data Management": ":material/database:",
    "Upload Financial Data": ":material/upload_file:",
    "User Management": ":material/manage_accounts:",
}


def _slug(page: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_")


def _go(page: str) -> None:
    st.session_state["active_page"] = page


def _toggle_dashboard() -> None:
    st.session_state["nav_dashboard_open"] = not st.session_state.get("nav_dashboard_open", True)


def _nav_item(page: str, current: str, icon: str | None = None) -> None:
    state = "navactive" if page == current else "navitem"
    with st.container(key=f"{state}_{_slug(page)}"):
        st.button(page, key=f"nav_{_slug(page)}", type="tertiary", icon=icon, width="stretch", on_click=_go, args=(page,))


def render_sidebar(role: str) -> str:
    pages = NAV_BY_ROLE.get(role, NAV_BY_ROLE["User"])
    current = st.session_state.get("active_page", pages[0])
    if current not in pages:
        current = pages[0]
        st.session_state["active_page"] = current
    dashboard = [page for page in pages if page in DASHBOARD_PAGES]
    others = [page for page in pages if page not in DASHBOARD_PAGES]
    is_open = st.session_state.get("nav_dashboard_open", True)

    with st.sidebar:
        st.markdown(f'<div class="sidebar-brand"><span class="brand-mark">FR</span><span>Financial Risk Analytics</span></div><div class="role-badge">{role}</div>', unsafe_allow_html=True)

        st.markdown('<div class="nav-group-label">Main</div>', unsafe_allow_html=True)
        parent_key = f"navparent_{'open' if is_open else 'closed'}{'_active' if current in dashboard else ''}"
        with st.container(key=parent_key):
            st.button("Dashboard", key="nav_dashboard_toggle", type="tertiary", icon=":material/space_dashboard:", width="stretch", on_click=_toggle_dashboard)
        if is_open:
            with st.container(key="nav_children"):
                for page in dashboard:
                    _nav_item(page, current)

        if others:
            st.markdown('<div class="nav-group-label">Manage</div>', unsafe_allow_html=True)
            for page in others:
                _nav_item(page, current, NAV_ICONS.get(page))

        if allowed(role, "export") and "analysis_data" in st.session_state:
            st.markdown('<div class="nav-group-label">Export</div>', unsafe_allow_html=True)
            export_frame = st.session_state["analysis_data"]
            with st.container(key="nav_exports"):
                st.download_button("Export CSV", export_csv(export_frame), "risk_analysis.csv", "text/csv", type="tertiary", icon=":material/download:", width="stretch")
                st.download_button("Export Excel", export_excel(export_frame), "risk_analysis.xlsx", type="tertiary", icon=":material/download:", width="stretch")

        st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
        if st.button("Sign out", width="stretch", key="sign_out", icon=":material/logout:"):
            st.session_state.pop("authenticated_role", None)
            st.rerun()
    return current
