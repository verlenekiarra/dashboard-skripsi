import pytest
import pandas as pd

from src.analytics.beneish import (
    AnalysisConfig,
    BASELINE_THRESHOLD,
    SENSITIVITY_THRESHOLD,
    calculate_indices,
    classify_beneish,
    analyze,
)


def sample_data() -> pd.DataFrame:
    values = {
        "Ticker": ["CPIN.JK", "CPIN.JK"],
        "CompanyName": ["CPIN", "CPIN"],
        "Sector": ["Manufacturing", "Manufacturing"],
        "FiscalYear": [2022, 2023],
        "TotalRevenue": [56867544, 61615850],
        "GrossProfit": [8144040, 8274512],
        "SellingGeneralAndAdministration": [1921368, 2089551],
        "ReconciledDepreciation": [315138, 328821],
        "NetIncome": [2928342, 2318584],
        "AccountsReceivable": [1553086, 1707909],
        "CurrentAssets": [17764298, 18324808],
        "NetPPE": [18301215, 18292726],
        "TotalAssets": [39847545, 40970800],
        "CurrentLiabilities": [10109335, 11123822],
        "LongTermDebt": [2311915, 1840533],
        "OperatingCashFlow": [1673887, 3146254],
    }
    return pd.DataFrame(values)


def test_cpin_indices_match_proposal_example():
    result = calculate_indices(sample_data()).iloc[1]
    assert result["DSRI"] == pytest.approx(1.0149, abs=0.001)
    assert result["GMI"] == pytest.approx(1.0664, abs=0.001)
    assert result["AQI"] == pytest.approx(1.1195, abs=0.001)
    assert result["SGI"] == pytest.approx(1.0835, abs=0.001)
    assert result["DEPI"] == pytest.approx(0.9587, abs=0.001)
    assert result["SGAI"] == pytest.approx(1.0037, abs=0.001)
    assert result["LVGI"] == pytest.approx(1.0151, abs=0.001)
    assert result["TATA"] == pytest.approx(-0.0202, abs=0.001)
    assert result["MScore"] == pytest.approx(-2.4133, abs=0.002)


def test_thresholds_are_distinct_and_strictly_greater():
    assert BASELINE_THRESHOLD == -1.78
    assert SENSITIVITY_THRESHOLD == -2.22
    scores = pd.Series([-1.78, -1.779, -2.22, -2.219, None])
    labels = classify_beneish(scores)
    assert labels.iloc[0] == "No potential earnings manipulation"
    assert labels.iloc[1] == "Potential earnings manipulation"
    assert labels.iloc[4] == "Insufficient data / not calculable"


def test_analysis_configuration_matches_proposal():
    config = AnalysisConfig()
    assert config.n_estimators == 200
    assert config.contamination == "auto"
    assert config.random_state == 42


def test_analysis_keeps_both_threshold_classifications():
    result = analyze(sample_data())
    row = result.loc[result["FiscalYear"].eq(2023)].iloc[0]
    assert row["Status_178"] == "No potential earnings manipulation"
    assert row["Status_222"] == "No potential earnings manipulation"
    assert row["RiskLabel"] == row["Status_178"]
