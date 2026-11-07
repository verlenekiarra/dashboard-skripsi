"""Login view. Credentials are verified server-side in src.auth.permissions."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.auth.permissions import authenticate, ensure_admin_user
from src.data.database import create_mysql_engine


def render_login() -> str | None:
    if st.session_state.get("authenticated_role"):
        return st.session_state["authenticated_role"]
    try:
        ensure_admin_user(create_mysql_engine())
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        pass
    column_left, column_center, column_right = st.columns([1, 1.5, 1])
    with column_center:
        st.markdown("### Manipulation Fraud Risk Dashboard")
        st.caption("Dashboard analitik risiko manipulasi laporan keuangan")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width="stretch")
        if submitted:
            role = authenticate(username, password)
            if role:
                st.session_state["authenticated_role"] = role
                st.rerun()
            st.error("Username atau password tidak valid.")
    return None
