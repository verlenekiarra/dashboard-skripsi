from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics.screening import screening_category
from src.ui.components.charts import render_screening_matrix
from src.ui.config import RANK_COLUMN_CONFIG


def render_risk_assessment(data: pd.DataFrame) -> None:
    st.markdown("### Risk Assessment")
    st.caption("Dua hasil screening ditampilkan berdampingan. Tidak ada composite risk score.")
    view = data.copy()
    view["ScreeningCategory"] = screening_category(view)
    columns = ["Ticker", "CompanyName", "FiscalYear", "RiskLabel", "AnomalyStatus", "ScreeningCategory", "MScore", "AnomalyScore"]
    available = [column for column in columns if column in view.columns]
    st.dataframe(view[available], width="stretch", hide_index=True, column_config=RANK_COLUMN_CONFIG)
    render_screening_matrix(view)
