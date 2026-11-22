from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, session, url_for)
from sqlalchemy import text

from flask_app.auth.decorators import login_required, permission_required
from src.analytics.beneish import AnalysisConfig, analyze
from src.analytics.screening import screening_category
from src.auth.permissions import (VALID_ROLES, create_user, list_users,
                                   set_user_active, update_user)
from src.data.database import create_mysql_engine
from src.data.io import export_csv, export_excel, read_upload
from src.data.repository import (database_counts, load_analysis, load_staging,
                                 read_analysis)
from src.data.statement_mapping import map_report_to_financials
from src.data.statement_report import read_statement_report

dashboard_bp = Blueprint("dashboard", __name__)


def _data() -> tuple[pd.DataFrame, str]:
    try:
        return read_analysis(create_mysql_engine()), ""
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def _filtered() -> tuple[pd.DataFrame, dict, str]:
    data, error = _data()
    years = request.args.getlist("year", type=int)
    tickers = request.args.getlist("ticker")
    sectors = request.args.getlist("sector")
    filtered = data
    if not data.empty:
        if years:
            filtered = filtered[filtered["FiscalYear"].isin(years)]
        if tickers:
            filtered = filtered[filtered["Ticker"].isin(tickers)]
        if sectors and "Sector" in filtered:
            filtered = filtered[filtered["Sector"].isin(sectors)]
    return filtered, {
        "years": sorted(data["FiscalYear"].dropna().unique().tolist()) if not data.empty else [],
        "tickers": sorted(data["Ticker"].dropna().unique().tolist()) if not data.empty else [],
        "sectors": sorted(data["Sector"].dropna().unique().tolist()) if not data.empty and "Sector" in data else [],
        "selected_years": years, "selected_tickers": tickers, "selected_sectors": sectors,
    }, error


def _chart(frame: pd.DataFrame, kind: str) -> str:
    if frame.empty:
        return ""
    if kind == "distribution":
        fig = px.histogram(frame.dropna(subset=["MScore"]), x="MScore", color="RiskLabel",
                           title="Beneish M-Score distribution", labels={"MScore": "M-Score"})
    else:
        fig = px.scatter(frame.dropna(subset=["MScore", "AnomalyScore"]), x="MScore",
                         y="AnomalyScore", color="ScreeningPriority", hover_name="Ticker",
                         title="M-Score versus Anomaly Score")
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _page(name: str, title: str, frame: pd.DataFrame | None = None, error: str = "", **extra):
    return render_template("dashboard/page.html", page=name, title=title, data=frame,
                           error=error, role=session.get("authenticated_role"), **extra)


@dashboard_bp.get("/")
def index():
    return redirect(url_for("dashboard.overview")) if session.get("authenticated_role") else redirect(url_for("auth.login"))


@dashboard_bp.get("/dashboard")
@login_required
def overview():
    data, filters, error = _filtered()
    metrics = {"companies": data["Ticker"].nunique() if not data.empty else 0,
               "observations": len(data),
               "beneish_flags": int(data["RiskLabel"].eq("Potential earnings manipulation").sum()) if not data.empty else 0,
               "anomalies": int(data["AnomalyLabel"].eq(-1).sum()) if not data.empty else 0}
    return _page("overview", "Overview", data, error, filters=filters, metrics=metrics,
                 charts={"distribution": _chart(data, "distribution"), "scatter": _chart(data, "scatter")})


@dashboard_bp.get("/beneish")
@permission_required("view")
def beneish():
    data, filters, error = _filtered()
    return _page("beneish", "Beneish M-Score", data, error, filters=filters,
                 chart=_chart(data, "distribution"))


@dashboard_bp.get("/anomaly")
@permission_required("view")
def anomaly():
    data, filters, error = _filtered()
    return _page("anomaly", "Anomaly Detection", data, error, filters=filters,
                 chart=_chart(data, "scatter"))


@dashboard_bp.get("/risk-assessment")
@permission_required("view")
def risk_assessment():
    data, filters, error = _filtered()
    if not data.empty:
        data = data.copy()
        data["ScreeningCategory"] = screening_category(data)
    return _page("risk", "Risk Assessment", data, error, filters=filters)


@dashboard_bp.get("/company-analysis")
@permission_required("view")
def company_analysis():
    data, filters, error = _filtered()
    ticker = request.args.get("company", "")
    if not ticker and filters["tickers"]:
        ticker = filters["tickers"][0]
    company = data[data["Ticker"].eq(ticker)] if ticker and not data.empty else data.iloc[0:0]
    charts = {"m_score": _chart(company, "distribution"), "anomaly": _chart(company, "scatter")}
    return _page("company", "Company Analysis", company, error, filters=filters, ticker=ticker, charts=charts)


@dashboard_bp.route("/upload", methods=["GET", "POST"])
@permission_required("upload")
def upload():
    preview = None
    if request.method == "POST":
        uploaded = request.files.get("file")
        mode = request.form.get("mode", "legacy")
        try:
            if not uploaded or not uploaded.filename:
                raise ValueError("Pilih file terlebih dahulu.")
            if mode == "report":
                report = read_statement_report(uploaded)
                ticker = request.form.get("ticker", "").strip()
                if not ticker:
                    raise ValueError("Ticker wajib diisi untuk printed report.")
                mapping = map_report_to_financials(report, ticker=ticker)
                if not mapping.is_complete:
                    raise ValueError("Akun laporan belum lengkap: " + ", ".join(mapping.unresolved))
                if request.form.get("confirmed") != "yes":
                    raise ValueError("Konfirmasi proses belum diberikan.")
                frame = analyze(mapping.frame, AnalysisConfig())
                load_analysis(create_mysql_engine(), frame)
                flash(f"{len(frame)} observasi printed report tersimpan.", "success")
            else:
                if request.form.get("confirmed") != "yes":
                    raise ValueError("Konfirmasi proses belum diberikan.")
                frame = read_upload(uploaded)
                analyzed = analyze(frame, AnalysisConfig())
                staging = None
                if uploaded.filename.lower().endswith((".xlsx", ".xls")):
                    uploaded.seek(0)
                    from src.data.io import read_workbook_long
                    staging = read_workbook_long(uploaded)
                engine = create_mysql_engine()
                if staging is not None:
                    load_staging(engine, staging)
                load_analysis(engine, analyzed)
                flash(f"{len(analyzed)} observasi tersimpan.", "success")
            return redirect(url_for("dashboard.upload"))
        except Exception as exc:
            flash(str(exc), "error")
    return _page("upload", "Upload Data", preview=preview)


@dashboard_bp.get("/data-management")
@permission_required("manage_system")
def data_management():
    data, error = _data()
    return _page("data-management", "Data Management", data, error,
                 counts=database_counts(create_mysql_engine()) if not error else {})


@dashboard_bp.post("/data-management/delete")
@permission_required("manage_system")
def delete_data():
    ticker, year = request.form.get("ticker"), request.form.get("year", type=int)
    with create_mysql_engine().begin() as connection:
        connection.execute(text("""
            DELETE FROM Fact_Risk_Analysis
            WHERE Company_ID = (SELECT Company_ID FROM Dim_Company WHERE Ticker_Code = :ticker)
              AND Time_ID = (SELECT Time_ID FROM Dim_Time WHERE Fiscal_Year = :year)
        """), {"ticker": ticker, "year": year})
    flash("Company-year result deleted.", "success")
    return redirect(url_for("dashboard.data_management"))


@dashboard_bp.route("/user-management", methods=["GET", "POST"])
@permission_required("manage_accounts")
def user_management():
    try:
        engine = create_mysql_engine()
    except Exception as exc:
        return _page("user-management", "User Management", users=[], roles=sorted(VALID_ROLES), error=str(exc))
    if request.method == "POST":
        try:
            action = request.form.get("action", "create")
            user_id = request.form.get("user_id", type=int)
            if action == "create":
                create_user(engine, request.form.get("username", ""), request.form.get("password", ""), request.form.get("role", "User"))
                flash("Account created.", "success")
            elif action == "update" and user_id:
                update_user(engine, user_id, request.form.get("role", "User"), request.form.get("password", ""))
                flash("Account updated.", "success")
            elif action == "toggle" and user_id:
                set_user_active(engine, user_id, request.form.get("active") == "true")
                flash("Account status updated.", "success")
        except Exception as exc:
            flash(str(exc), "error")
    return _page("user-management", "User Management", users=list_users(engine), roles=sorted(VALID_ROLES))


@dashboard_bp.get("/export/<format>")
@permission_required("export")
def export_data(format: str):
    data, _ = _data()
    if format not in {"csv", "xlsx"}:
        return "Unsupported export format", 400
    content = export_csv(data) if format == "csv" else export_excel(data)
    return send_file(BytesIO(content), as_attachment=True,
                     download_name=f"risk-analysis.{format}",
                     mimetype="text/csv" if format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
