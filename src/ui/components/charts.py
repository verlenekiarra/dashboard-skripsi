"""Chart renderers. Colors come from the active theme palette."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.beneish import BASELINE_THRESHOLD, SENSITIVITY_THRESHOLD
from src.analytics.screening import screening_category
from src.ui.theme import chart_palette


def render_mscore_trend(data: pd.DataFrame) -> None:
    trend = data.groupby("FiscalYear", as_index=False).agg({"MScore": "mean"}).dropna()
    if trend.empty:
        st.info("Not enough data for the trend chart.")
        return
    palette = chart_palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["FiscalYear"], y=trend["MScore"], mode="lines+markers", name="Avg M-Score", line=dict(color=palette["line"], width=2), marker=dict(size=8)))
    fig.add_hline(y=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"], annotation_text="Threshold -1.78")
    fig.add_hline(y=SENSITIVITY_THRESHOLD, line_dash="dot", line_color=palette["sensitivity"], annotation_text="Sensitivity -2.22")
    fig.update_layout(title="Beneish M-Score Analysis by Year", height=340, margin=dict(l=35, r=20, t=55, b=35), autosize=True, xaxis_title="Year", yaxis_title="M-Score", plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"], font=dict(family="Plus Jakarta Sans", color=palette["text"]), title_font=dict(family="Plus Jakarta Sans", color=palette["title"], size=15))
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "responsive": True})


def render_scatter(data: pd.DataFrame) -> None:
    plot_data = data.dropna(subset=["MScore", "AnomalyScore"]).copy()
    if plot_data.empty:
        st.info("Not enough data for the scatter plot.")
        return
    palette = chart_palette()
    fig = px.scatter(plot_data, x="AnomalyScore", y="MScore", color="ScreeningPriority", hover_name="Ticker", hover_data=["FiscalYear", "RiskLabel", "AnomalyStatus"], color_discrete_map=palette["tiers"])
    fig.add_hline(y=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"])
    fig.update_layout(title="M-Score vs Anomaly Score", height=340, margin=dict(l=35, r=20, t=55, b=45), autosize=True, xaxis_title="Anomaly Score", yaxis_title="Beneish M-Score", legend_title="Status", plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"], font=dict(family="Plus Jakarta Sans", color=palette["text"]), title_font=dict(family="Plus Jakarta Sans", color=palette["title"], size=15), legend=dict(orientation="h", yanchor="bottom", y=-0.32, xanchor="left", x=0))
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "responsive": True})


def chart_layout(fig: go.Figure, title: str, palette: dict, height: int = 340) -> go.Figure:
    fig.update_layout(
        title=title, height=height, margin=dict(l=35, r=20, t=55, b=35), autosize=True,
        plot_bgcolor=palette["surface"], paper_bgcolor=palette["surface"],
        font=dict(family="Plus Jakarta Sans", color=palette["text"]),
        title_font=dict(family="Plus Jakarta Sans", color=palette["title"], size=15),
        hoverlabel=dict(font=dict(family="Plus Jakarta Sans", size=12)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["zero"])
    return fig


def render_mscore_distribution(data: pd.DataFrame) -> None:
    values = data.dropna(subset=["MScore"])
    if values.empty:
        st.info("No M-Score data is available for visualization.")
        return
    palette = chart_palette()
    fig = px.histogram(values, x="MScore", nbins=24, color_discrete_sequence=[palette["line"]])
    fig.add_vline(x=BASELINE_THRESHOLD, line_dash="dash", line_color=palette["baseline"], annotation_text="Threshold")
    st.plotly_chart(chart_layout(fig, "Distribusi Beneish M-Score", palette), width="stretch", config={"displaylogo": False, "responsive": True})


def render_anomaly_distribution(data: pd.DataFrame) -> None:
    values = data.dropna(subset=["AnomalyScore"])
    if values.empty:
        st.info("No Anomaly Score data is available for visualization.")
        return
    palette = chart_palette()
    fig = px.histogram(values, x="AnomalyScore", nbins=24, color_discrete_sequence=[palette["line"]])
    st.plotly_chart(chart_layout(fig, "Distribusi Anomaly Score", palette), width="stretch", config={"displaylogo": False, "responsive": True})


def render_screening_matrix(data: pd.DataFrame) -> None:
    categories = screening_category(data).value_counts().rename_axis("Screening category").reset_index(name="Observations")
    st.dataframe(categories, width="stretch", hide_index=True)
    st.caption("Not indicated by either method means the observation did not cross the Beneish threshold and was labeled normal by Isolation Forest. It is not proof that manipulation is impossible.")
    palette = chart_palette()
    fig = px.bar(categories, x="Screening category", y="Observations", color="Screening category", color_discrete_sequence=[palette["line"], palette["baseline"], palette["sensitivity"], palette["tiers"]["Low priority"]])
    st.plotly_chart(chart_layout(fig, "Independent screening results", palette), width="stretch", config={"displaylogo": False, "responsive": True})
