from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

INDEX_COLUMNS: Final[tuple[str, ...]] = ("DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA")
FINANCIAL_COLUMNS: Final[tuple[str, ...]] = (
    "TotalRevenue", "GrossProfit", "SellingGeneralAndAdministration", "ReconciledDepreciation",
    "NetIncome", "AccountsReceivable", "CurrentAssets", "NetPPE", "TotalAssets",
    "CurrentLiabilities", "LongTermDebt", "OperatingCashFlow",
)
BASELINE_THRESHOLD: Final[float] = -1.78
SENSITIVITY_THRESHOLD: Final[float] = -2.22

# Review order, not a composite score: tier 1 is flagged by both methods.
SCREENING_TIERS: Final[dict[str, int]] = {
    "Priority screening": 1,
    "Beneish flag": 2,
    "Anomaly flag": 3,
    "Low priority": 4,
    "Insufficient data / not calculable": 5,
}

@dataclass(frozen=True)
class AnalysisConfig:
    threshold: float = BASELINE_THRESHOLD
    n_estimators: int = 200
    contamination: str = "auto"
    random_state: int = 42


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)


def validate_financial_data(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    result = frame.copy()
    result["FiscalYear"] = pd.to_numeric(result["FiscalYear"], errors="coerce").astype("Int64")
    for column in FINANCIAL_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.drop_duplicates(subset=["Ticker", "FiscalYear"], keep="last")
    return result.sort_values(["Ticker", "FiscalYear"]).reset_index(drop=True)


def calculate_indices(frame: pd.DataFrame) -> pd.DataFrame:
    data = validate_financial_data(frame)
    grouped = data.groupby("Ticker", group_keys=False)
    previous = grouped[list(FINANCIAL_COLUMNS)].shift(1)
    current = data[list(FINANCIAL_COLUMNS)]
    result = data[["Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS]].copy()
    revenue = current["TotalRevenue"]
    previous_revenue = previous["TotalRevenue"]
    gross_margin = _ratio(current["GrossProfit"], revenue)
    previous_gross_margin = _ratio(previous["GrossProfit"], previous_revenue)
    result["DSRI"] = _ratio(_ratio(current["AccountsReceivable"], revenue), _ratio(previous["AccountsReceivable"], previous_revenue))
    result["GMI"] = _ratio(previous_gross_margin, gross_margin)
    result["AQI"] = _ratio(1 - _ratio(current["CurrentAssets"] + current["NetPPE"], current["TotalAssets"]), 1 - _ratio(previous["CurrentAssets"] + previous["NetPPE"], previous["TotalAssets"]))
    result["SGI"] = _ratio(revenue, previous_revenue)
    result["DEPI"] = _ratio(_ratio(previous["ReconciledDepreciation"], previous["ReconciledDepreciation"] + previous["NetPPE"]), _ratio(current["ReconciledDepreciation"], current["ReconciledDepreciation"] + current["NetPPE"]))
    result["SGAI"] = _ratio(_ratio(current["SellingGeneralAndAdministration"], revenue), _ratio(previous["SellingGeneralAndAdministration"], previous_revenue))
    result["LVGI"] = _ratio(_ratio(current["CurrentLiabilities"] + current["LongTermDebt"], current["TotalAssets"]), _ratio(previous["CurrentLiabilities"] + previous["LongTermDebt"], previous["TotalAssets"]))
    result["TATA"] = _ratio(current["NetIncome"] - current["OperatingCashFlow"], current["TotalAssets"])
    result["MScore"] = (-4.84 + 0.920 * result["DSRI"] + 0.528 * result["GMI"] + 0.404 * result["AQI"] + 0.892 * result["SGI"] + 0.115 * result["DEPI"] - 0.172 * result["SGAI"] - 0.327 * result["LVGI"] + 4.679 * result["TATA"])
    return result.replace([np.inf, -np.inf], np.nan)


def classify_beneish(scores: pd.Series, threshold: float = BASELINE_THRESHOLD) -> pd.Series:
    return pd.Series(np.select([scores.isna(), scores > threshold], ["Insufficient data / not calculable", "Potential earnings manipulation"], default="No potential earnings manipulation"), index=scores.index)


def run_anomaly_detection(frame: pd.DataFrame, config: AnalysisConfig = AnalysisConfig()) -> pd.DataFrame:
    result = frame.copy()
    complete = result[list(INDEX_COLUMNS)].notna().all(axis=1)
    result["AnomalyScore"] = np.nan
    result["AnomalyLabel"] = pd.Series(pd.array([pd.NA] * len(result), dtype="Int64"), index=result.index)
    result["AnomalyStatus"] = "Insufficient data / not calculable"
    if complete.sum() == 0:
        return result
    model = IsolationForest(n_estimators=config.n_estimators, contamination=config.contamination, random_state=config.random_state)
    features = result.loc[complete, list(INDEX_COLUMNS)]
    model.fit(features)
    result.loc[complete, "AnomalyScore"] = -model.score_samples(features)
    result.loc[complete, "AnomalyLabel"] = model.predict(features)
    anomaly_label = result["AnomalyLabel"].astype("Int64")
    result["AnomalyStatus"] = np.select(
        [anomaly_label.eq(-1).fillna(False).to_numpy(dtype=bool), anomaly_label.eq(1).fillna(False).to_numpy(dtype=bool)],
        ["Anomaly", "Normal"],
        default="Insufficient data / not calculable",
    )
    return result


def analyze(frame: pd.DataFrame, config: AnalysisConfig = AnalysisConfig()) -> pd.DataFrame:
    result = calculate_indices(frame)
    result["Status_178"] = classify_beneish(result["MScore"], BASELINE_THRESHOLD)
    result["Status_222"] = classify_beneish(result["MScore"], SENSITIVITY_THRESHOLD)
    result["RiskLabel"] = result["Status_178"]
    result = run_anomaly_detection(result, config)
    risk_flag = result["RiskLabel"].eq("Potential earnings manipulation").fillna(False).to_numpy(dtype=bool)
    anomaly_flag = result["AnomalyLabel"].eq(-1).fillna(False).to_numpy(dtype=bool)
    incomplete = (result["MScore"].isna() | result["AnomalyLabel"].isna()).to_numpy(dtype=bool)
    result["ScreeningPriority"] = np.select(
        [risk_flag & anomaly_flag, risk_flag, anomaly_flag, incomplete],
        ["Priority screening", "Beneish flag", "Anomaly flag", "Insufficient data / not calculable"],
        default="Low priority",
    )
    return rank_screening(result)


def rank_screening(frame: pd.DataFrame) -> pd.DataFrame:
    """Order observations for review.

    Lexicographic, not a composite score: screening tier decides first, then
    M-Score (descending), then anomaly score (descending). M-Score and anomaly
    score are never combined into one number.
    """
    result = frame.copy()
    result["ScreeningTier"] = result["ScreeningPriority"].map(SCREENING_TIERS).astype("Int64")
    ordered = result.sort_values(
        ["ScreeningTier", "MScore", "AnomalyScore", "Ticker", "FiscalYear"],
        ascending=[True, False, False, True, True],
        na_position="last",
        kind="mergesort",
    )
    calculable = ordered.index[ordered["ScreeningPriority"].ne("Insufficient data / not calculable")]
    result["RiskRank"] = pd.Series(range(1, len(calculable) + 1), index=calculable, dtype="Int64")
    return result
