from __future__ import annotations

import streamlit as st


def render_placeholder_page(title: str, message: str) -> None:
    st.markdown(f"### {title}")
    st.info(message)
