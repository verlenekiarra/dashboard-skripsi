from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.data.database import create_mysql_engine
from src.data.io import read_upload
from src.data.repository import read_analysis


def load_data() -> pd.DataFrame:
    if "financial_data" in st.session_state:
        return st.session_state["financial_data"]
    try:
        data = read_analysis(create_mysql_engine())
        if not data.empty:
            st.session_state["financial_data"] = data
            st.session_state["data_source"] = "MySQL"
            return data
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        pass
    default_path = Path(".agents/skills/docs/skripsi_rawwwwwwwww_ajajaja.xlsx")
    if default_path.exists():
        try:
            source = BytesIO(default_path.read_bytes())
            source.name = default_path.name
            data = read_upload(source)
            st.session_state["financial_data"] = data
            st.session_state["data_source"] = "Local workbook"
            return data
        except (AttributeError, OSError, ValueError):
            pass
    return pd.DataFrame()
