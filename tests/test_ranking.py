import pandas as pd

from src.analytics.beneish import SCREENING_TIERS, rank_screening


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_tier_decides_before_scores():
    data = frame([
        {"Ticker": "AAA", "FiscalYear": 2024, "MScore": -3.0, "AnomalyScore": 0.31, "ScreeningPriority": "Priority screening"},
        {"Ticker": "BBB", "FiscalYear": 2024, "MScore": 9.0, "AnomalyScore": 0.60, "ScreeningPriority": "Beneish flag"},
    ])
    ranked = rank_screening(data).set_index("Ticker")
    assert ranked.loc["AAA", "RiskRank"] == 1
    assert ranked.loc["BBB", "RiskRank"] == 2


def test_mscore_breaks_tie_inside_same_tier():
    data = frame([
        {"Ticker": "LOW", "FiscalYear": 2024, "MScore": -1.0, "AnomalyScore": 0.90, "ScreeningPriority": "Beneish flag"},
        {"Ticker": "HIGH", "FiscalYear": 2024, "MScore": 4.0, "AnomalyScore": 0.32, "ScreeningPriority": "Beneish flag"},
    ])
    ranked = rank_screening(data).set_index("Ticker")
    assert ranked.loc["HIGH", "RiskRank"] == 1
    assert ranked.loc["LOW", "RiskRank"] == 2


def test_anomaly_score_breaks_tie_when_mscore_equal():
    data = frame([
        {"Ticker": "CALM", "FiscalYear": 2024, "MScore": 2.0, "AnomalyScore": 0.33, "ScreeningPriority": "Beneish flag"},
        {"Ticker": "ODD", "FiscalYear": 2024, "MScore": 2.0, "AnomalyScore": 0.58, "ScreeningPriority": "Beneish flag"},
    ])
    ranked = rank_screening(data).set_index("Ticker")
    assert ranked.loc["ODD", "RiskRank"] == 1
    assert ranked.loc["CALM", "RiskRank"] == 2


def test_insufficient_data_is_not_ranked():
    data = frame([
        {"Ticker": "OK", "FiscalYear": 2024, "MScore": -2.0, "AnomalyScore": 0.33, "ScreeningPriority": "Low priority"},
        {"Ticker": "GAP", "FiscalYear": 2024, "MScore": None, "AnomalyScore": None, "ScreeningPriority": "Insufficient data / not calculable"},
    ])
    ranked = rank_screening(data).set_index("Ticker")
    assert ranked.loc["OK", "RiskRank"] == 1
    assert pd.isna(ranked.loc["GAP", "RiskRank"])


def test_ranks_are_unique_and_tiers_ordered():
    data = frame([
        {"Ticker": "A", "FiscalYear": 2024, "MScore": 1.0, "AnomalyScore": 0.5, "ScreeningPriority": "Anomaly flag"},
        {"Ticker": "B", "FiscalYear": 2024, "MScore": 1.0, "AnomalyScore": 0.5, "ScreeningPriority": "Priority screening"},
        {"Ticker": "C", "FiscalYear": 2024, "MScore": 1.0, "AnomalyScore": 0.5, "ScreeningPriority": "Low priority"},
    ])
    ranked = rank_screening(data).set_index("Ticker")
    assert ranked["RiskRank"].dropna().duplicated().sum() == 0
    assert ranked.loc["B", "RiskRank"] < ranked.loc["A", "RiskRank"] < ranked.loc["C", "RiskRank"]
    assert SCREENING_TIERS["Priority screening"] < SCREENING_TIERS["Anomaly flag"]
