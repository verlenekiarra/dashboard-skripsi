from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.analytics.beneish import SCREENING_TIERS, rank_screening


def _records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict("records")


def load_staging(engine: Engine, frame: pd.DataFrame) -> int:
    required = {"Ticker", "Statement", "Item", "Year", "Value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing staging columns: {', '.join(missing)}")
    data = frame[["Ticker", "Statement", "Item", "Year", "Value"]].copy()
    data.columns = ["Ticker_Code", "Statement_Name", "Item_Name", "Fiscal_Year", "Value"]
    data["Fiscal_Year"] = pd.to_numeric(data["Fiscal_Year"], errors="coerce").astype("Int64")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    data = data.dropna(subset=["Ticker_Code", "Statement_Name", "Item_Name", "Fiscal_Year"])
    data = data.drop_duplicates(["Ticker_Code", "Statement_Name", "Item_Name", "Fiscal_Year"])
    rows = _records(data)
    if not rows:
        return 0
    statement = text("""
        INSERT INTO Stg_Financial_Statement
            (Ticker_Code, Statement_Name, Item_Name, Fiscal_Year, Value)
        VALUES (:Ticker_Code, :Statement_Name, :Item_Name, :Fiscal_Year, :Value)
        ON CONFLICT (Ticker_Code, Statement_Name, Item_Name, Fiscal_Year)
        DO UPDATE SET Value = EXCLUDED.Value, Loaded_At = CURRENT_TIMESTAMP
    """ if engine.dialect.name == "postgresql" else """
        INSERT INTO Stg_Financial_Statement
            (Ticker_Code, Statement_Name, Item_Name, Fiscal_Year, Value)
        VALUES (:Ticker_Code, :Statement_Name, :Item_Name, :Fiscal_Year, :Value)
        ON DUPLICATE KEY UPDATE
            Value = VALUES(Value), Loaded_At = CURRENT_TIMESTAMP
    """)
    with engine.begin() as connection:
        connection.execute(statement, rows)
    return len(rows)


def load_analysis(engine: Engine, frame: pd.DataFrame, *, replace_existing: bool = False) -> int:
    required = {
        "Ticker", "CompanyName", "Sector", "FiscalYear", "MScore",
        "Status_178", "Status_222", "AnomalyLabel", "AnomalyScore",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing analysis columns: {', '.join(missing)}")

    companies = frame[["Ticker", "CompanyName", "Sector"]].drop_duplicates("Ticker").copy()
    companies["SubSector"] = None
    years = sorted(int(year) for year in frame["FiscalYear"].dropna().unique())

    company_statement = text("""
        INSERT INTO Dim_Company
            (Ticker_Code, Company_Name, Sector, Sub_Sector)
        VALUES (:Ticker, :CompanyName, :Sector, :SubSector)
        ON CONFLICT (Ticker_Code) DO UPDATE SET
            Company_Name = EXCLUDED.Company_Name,
            Sector = EXCLUDED.Sector,
            Sub_Sector = EXCLUDED.Sub_Sector
    """ if engine.dialect.name == "postgresql" else """
        INSERT INTO Dim_Company
            (Ticker_Code, Company_Name, Sector, Sub_Sector)
        VALUES (:Ticker, :CompanyName, :Sector, :SubSector)
        ON DUPLICATE KEY UPDATE
            Company_Name = VALUES(Company_Name),
            Sector = VALUES(Sector),
            Sub_Sector = VALUES(Sub_Sector)
    """)
    time_statement = text("""
        INSERT INTO Dim_Time (Time_ID, Fiscal_Year)
        VALUES (:Time_ID, :Fiscal_Year)
        ON CONFLICT (Time_ID) DO UPDATE SET Fiscal_Year = EXCLUDED.Fiscal_Year
    """ if engine.dialect.name == "postgresql" else """
        INSERT INTO Dim_Time (Time_ID, Fiscal_Year)
        VALUES (:Time_ID, :Fiscal_Year)
        ON DUPLICATE KEY UPDATE Fiscal_Year = VALUES(Fiscal_Year)
    """)
    fact_statement = text("""
        INSERT INTO Fact_Risk_Analysis (
            Company_ID, Time_ID, Total_Revenue, Total_Receivables,
            Cost_of_Goods_Sold, Gross_Profit, Current_Assets, Net_PPE,
            Total_Assets, Depreciation_Expense, SGA_Expense,
            Total_Liabilities, Net_Income, Operating_Cash_Flow,
            DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA, M_Score,
            Status_178, Status_222, Anomaly_Label, Anomaly_Score
        )
        SELECT
            c.Company_ID, :Time_ID, :Total_Revenue, :Total_Receivables,
            :Cost_of_Goods_Sold, :Gross_Profit, :Current_Assets, :Net_PPE,
            :Total_Assets, :Depreciation_Expense, :SGA_Expense,
            :Total_Liabilities, :Net_Income, :Operating_Cash_Flow,
            :DSRI, :GMI, :AQI, :SGI, :DEPI, :SGAI, :LVGI, :TATA, :M_Score,
            :Status_178, :Status_222, :Anomaly_Label, :Anomaly_Score
        FROM Dim_Company c
        WHERE c.Ticker_Code = :Ticker_Code
        ON CONFLICT (Company_ID, Time_ID) DO UPDATE SET
            Total_Revenue = EXCLUDED.Total_Revenue,
            Total_Receivables = EXCLUDED.Total_Receivables,
            Cost_of_Goods_Sold = EXCLUDED.Cost_of_Goods_Sold,
            Gross_Profit = EXCLUDED.Gross_Profit,
            Current_Assets = EXCLUDED.Current_Assets, Net_PPE = EXCLUDED.Net_PPE,
            Total_Assets = EXCLUDED.Total_Assets,
            Depreciation_Expense = EXCLUDED.Depreciation_Expense,
            SGA_Expense = EXCLUDED.SGA_Expense,
            Total_Liabilities = EXCLUDED.Total_Liabilities,
            Net_Income = EXCLUDED.Net_Income,
            Operating_Cash_Flow = EXCLUDED.Operating_Cash_Flow,
            DSRI = EXCLUDED.DSRI, GMI = EXCLUDED.GMI, AQI = EXCLUDED.AQI,
            SGI = EXCLUDED.SGI, DEPI = EXCLUDED.DEPI, SGAI = EXCLUDED.SGAI,
            LVGI = EXCLUDED.LVGI, TATA = EXCLUDED.TATA, M_Score = EXCLUDED.M_Score,
            Status_178 = EXCLUDED.Status_178, Status_222 = EXCLUDED.Status_222,
            Anomaly_Label = EXCLUDED.Anomaly_Label,
            Anomaly_Score = EXCLUDED.Anomaly_Score
    """ if engine.dialect.name == "postgresql" else """
        INSERT INTO Fact_Risk_Analysis (
            Company_ID, Time_ID, Total_Revenue, Total_Receivables,
            Cost_of_Goods_Sold, Gross_Profit, Current_Assets, Net_PPE,
            Total_Assets, Depreciation_Expense, SGA_Expense,
            Total_Liabilities, Net_Income, Operating_Cash_Flow,
            DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA, M_Score,
            Status_178, Status_222, Anomaly_Label, Anomaly_Score
        )
        SELECT
            c.Company_ID, :Time_ID, :Total_Revenue, :Total_Receivables,
            :Cost_of_Goods_Sold, :Gross_Profit, :Current_Assets, :Net_PPE,
            :Total_Assets, :Depreciation_Expense, :SGA_Expense,
            :Total_Liabilities, :Net_Income, :Operating_Cash_Flow,
            :DSRI, :GMI, :AQI, :SGI, :DEPI, :SGAI, :LVGI, :TATA, :M_Score,
            :Status_178, :Status_222, :Anomaly_Label, :Anomaly_Score
        FROM Dim_Company c
        WHERE c.Ticker_Code = :Ticker_Code
        ON DUPLICATE KEY UPDATE
            Total_Revenue = VALUES(Total_Revenue), Total_Receivables = VALUES(Total_Receivables),
            Cost_of_Goods_Sold = VALUES(Cost_of_Goods_Sold), Gross_Profit = VALUES(Gross_Profit),
            Current_Assets = VALUES(Current_Assets), Net_PPE = VALUES(Net_PPE), Total_Assets = VALUES(Total_Assets),
            Depreciation_Expense = VALUES(Depreciation_Expense), SGA_Expense = VALUES(SGA_Expense),
            Total_Liabilities = VALUES(Total_Liabilities), Net_Income = VALUES(Net_Income),
            Operating_Cash_Flow = VALUES(Operating_Cash_Flow), DSRI = VALUES(DSRI), GMI = VALUES(GMI),
            AQI = VALUES(AQI), SGI = VALUES(SGI), DEPI = VALUES(DEPI), SGAI = VALUES(SGAI),
            LVGI = VALUES(LVGI), TATA = VALUES(TATA), M_Score = VALUES(M_Score),
            Status_178 = VALUES(Status_178), Status_222 = VALUES(Status_222),
            Anomaly_Label = VALUES(Anomaly_Label), Anomaly_Score = VALUES(Anomaly_Score)
    """)

    facts = pd.DataFrame({
        "Ticker_Code": frame["Ticker"],
        "Time_ID": frame["FiscalYear"],
        "Total_Revenue": frame["TotalRevenue"],
        "Total_Receivables": frame["AccountsReceivable"],
        "Cost_of_Goods_Sold": frame["TotalRevenue"] - frame["GrossProfit"],
        "Gross_Profit": frame["GrossProfit"],
        "Current_Assets": frame["CurrentAssets"],
        "Net_PPE": frame["NetPPE"],
        "Total_Assets": frame["TotalAssets"],
        "Depreciation_Expense": frame["ReconciledDepreciation"],
        "SGA_Expense": frame["SellingGeneralAndAdministration"],
        # Source workbook has no TotalLiabilities item. Keep metadata column null.
        "Total_Liabilities": None,
        "Net_Income": frame["NetIncome"],
        "Operating_Cash_Flow": frame["OperatingCashFlow"],
        "DSRI": frame["DSRI"], "GMI": frame["GMI"], "AQI": frame["AQI"],
        "SGI": frame["SGI"], "DEPI": frame["DEPI"], "SGAI": frame["SGAI"],
        "LVGI": frame["LVGI"], "TATA": frame["TATA"],
        "M_Score": frame["MScore"], "Status_178": frame["Status_178"],
        "Status_222": frame["Status_222"],
        "Anomaly_Label": frame["AnomalyLabel"],
        "Anomaly_Score": frame["AnomalyScore"],
    }).replace([np.inf, -np.inf], np.nan)

    with engine.begin() as connection:
        connection.execute(company_statement, _records(companies))
        connection.execute(time_statement, [{"Time_ID": year, "Fiscal_Year": year} for year in years])
        if replace_existing:
            connection.execute(text("DELETE FROM Fact_Risk_Analysis"))
        connection.execute(fact_statement, _records(facts))
    return len(facts)


def read_analysis(engine: Engine) -> pd.DataFrame:
    query = text("""
        SELECT
            c.Ticker_Code AS "Ticker",
            c.Company_Name AS "CompanyName",
            c.Sector AS "Sector",
            c.Sub_Sector AS "SubSector",
            t.Fiscal_Year AS "FiscalYear",
            f.DSRI AS "DSRI", f.GMI AS "GMI", f.AQI AS "AQI", f.SGI AS "SGI",
            f.DEPI AS "DEPI", f.SGAI AS "SGAI", f.LVGI AS "LVGI", f.TATA AS "TATA",
            f.M_Score AS "MScore",
            f.Status_178 AS "Status_178", f.Status_222 AS "Status_222",
            f.Status_178 AS "RiskLabel",
            f.Anomaly_Score AS "AnomalyScore",
            f.Anomaly_Label AS "AnomalyLabel"
        FROM Fact_Risk_Analysis f
        JOIN Dim_Company c ON c.Company_ID = f.Company_ID
        JOIN Dim_Time t ON t.Time_ID = f.Time_ID
        ORDER BY t.Fiscal_Year, c.Ticker_Code
    """)
    frame = pd.read_sql(query, engine)
    if frame.empty:
        return frame
    frame["AnomalyLabel"] = pd.to_numeric(frame["AnomalyLabel"], errors="coerce").astype("Int64")
    frame["AnomalyStatus"] = np.select(
        [frame["AnomalyLabel"].eq(-1).fillna(False), frame["AnomalyLabel"].eq(1).fillna(False)],
        ["Anomaly", "Normal"],
        default="Insufficient data / not calculable",
    )
    risk = frame["RiskLabel"].eq("Potential earnings manipulation").fillna(False)
    anomaly = frame["AnomalyLabel"].eq(-1).fillna(False)
    incomplete = frame["MScore"].isna() | frame["AnomalyLabel"].isna()
    frame["ScreeningPriority"] = np.select(
        [risk & anomaly, risk, anomaly, incomplete],
        ["Priority screening", "Beneish flag", "Anomaly flag", "Insufficient data / not calculable"],
        default="Low priority",
    )
    return rank_screening(frame)


def database_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table: int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
            for table in ("Stg_Financial_Statement", "Dim_Company", "Dim_Time", "Fact_Risk_Analysis")
        }
