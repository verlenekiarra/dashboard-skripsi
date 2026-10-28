from __future__ import annotations

import io

import pandas as pd

from src.analytics.beneish import (
    BASELINE_THRESHOLD,
    FINANCIAL_COLUMNS,
    SENSITIVITY_THRESHOLD,
    classify_beneish,
)

REQUIRED_UPLOAD_COLUMNS = {"Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS}
STATEMENT_SHEETS = ("Income Statement", "Balance Sheet", "Cash Flow")
ITEM_ALIASES = {"CashFlowsfromusedinOperatingActivitiesDirect": "OperatingCashFlow"}


def read_workbook_long(uploaded_file) -> pd.DataFrame:
    uploaded_file.seek(0)
    sheets = pd.read_excel(uploaded_file, sheet_name=list(STATEMENT_SHEETS))
    frames = []
    for statement, frame in sheets.items():
        frame = frame.copy()
        frame["Statement"] = statement
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _prepare_long_financial_data(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Ticker", "Year", "Item", "Value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    data = frame.copy()
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    data["Item"] = data["Item"].replace(ITEM_ALIASES)
    data = data.drop_duplicates(["Ticker", "Year", "Item"], keep="first")
    pivot = data[data["Item"].isin(FINANCIAL_COLUMNS)].pivot_table(
        index=["Ticker", "Year"], columns="Item", values="Value", aggfunc="first"
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={"Year": "FiscalYear"})
    pivot["CompanyName"] = pivot["Ticker"]
    pivot["Sector"] = "Manufacturing"
    missing_items = sorted(set(FINANCIAL_COLUMNS).difference(pivot.columns))
    for column in missing_items:
        pivot[column] = pd.NA
    return pivot[["Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS]]


def read_upload(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        frame = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        frame = read_workbook_long(uploaded_file)
    else:
        raise ValueError("Supported upload formats are CSV and Excel")
    if {"Ticker", "Year", "Item", "Value"}.issubset(frame.columns):
        return _prepare_long_financial_data(frame)
    missing = sorted(REQUIRED_UPLOAD_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return frame


def read_validated_analysis_workbook(path_or_buffer) -> pd.DataFrame:
    sheets = pd.read_excel(
        path_or_buffer,
        sheet_name=["Final Results", "Calculation Data"],
    )
    final = sheets["Final Results"].copy()
    calculation = sheets["Calculation Data"].copy()
    if final.duplicated(["Ticker", "Year"]).any():
        raise ValueError("Final Results contains duplicate Ticker-Year rows")
    if calculation.duplicated(["Ticker", "Year"]).any():
        raise ValueError("Calculation Data contains duplicate Ticker-Year rows")

    result = final.merge(calculation, on=["Ticker", "Year"], how="left", validate="one_to_one")
    if result["TotalRevenue"].isna().all():
        raise ValueError("Final Results cannot be matched to Calculation Data")
    result = result.rename(columns={
        "Year": "FiscalYear",
        "M-Score": "MScore",
        "Anomaly_Label": "AnomalyLabel",
        "Anomaly_Score": "AnomalyScore",
        "CashFlowsfromusedinOperatingActivitiesDirect": "OperatingCashFlow",
    })
    result["CompanyName"] = result["Ticker"]
    result["Sector"] = "Manufacturing"
    result["Status_178"] = classify_beneish(result["MScore"], BASELINE_THRESHOLD)
    result["Status_222"] = classify_beneish(result["MScore"], SENSITIVITY_THRESHOLD)
    required = [
        "Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS,
        "DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA",
        "MScore", "Status_178", "Status_222", "AnomalyLabel", "AnomalyScore",
    ]
    missing = sorted(set(required).difference(result.columns))
    if missing:
        raise ValueError(f"Validated workbook is missing columns: {', '.join(missing)}")
    return result[required]


def export_csv(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def export_excel(frame: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Risk Analysis")
    return output.getvalue()
