from pathlib import Path

import pandas as pd
import pytest

from src.analytics.beneish import FINANCIAL_COLUMNS, AnalysisConfig, analyze
from src.analytics.population_scoring import analyze_against_population
from src.data.statement_mapping import map_report_to_financials
from src.data.statement_report import read_statement_report

REFERENCE = Path.home() / "Downloads" / "04b Kimia Farma.xlsx"
SHEET = "LK Kimia Farma"

pytestmark = pytest.mark.skipif(
    not REFERENCE.exists(),
    reason="Reference workbook is not available on this machine",
)


@pytest.fixture(scope="module")
def report() -> pd.DataFrame:
    return read_statement_report(REFERENCE, sheet_name=SHEET)


@pytest.fixture(scope="module")
def mapped(report):
    return map_report_to_financials(report, ticker="TEST")


def test_every_beneish_input_is_resolved(mapped):
    assert mapped.unresolved == ()
    assert mapped.is_complete
    assert set(mapped.resolved) == set(FINANCIAL_COLUMNS)


def test_mapped_values_match_the_reported_accounts(mapped):
    frame = mapped.frame.set_index("FiscalYear")
    assert frame.loc[2003, "TotalRevenue"] == 1816384      # PENJUALAN BERSIH
    assert frame.loc[2004, "NetIncome"] == 77756           # LABA BERSIH
    assert frame.loc[2006, "TotalAssets"] == 1261226       # JUMLAH AKTIVA
    assert frame.loc[2005, "CurrentAssets"] == 677862      # Jumlah Aktiva Lancar
    assert frame.loc[2004, "OperatingCashFlow"] == -75046  # Kas Bersih Akt. Operasi


def test_mapping_carries_identity_and_every_period(mapped):
    assert mapped.frame["Ticker"].unique().tolist() == ["TEST"]
    assert "KIMIA FARMA" in mapped.frame["CompanyName"].iloc[0].upper()
    assert sorted(mapped.frame["FiscalYear"].tolist()) == [2003, 2004, 2005, 2006]


def test_mapped_frame_satisfies_the_analytics_contract(mapped):
    required = {"Ticker", "CompanyName", "Sector", "FiscalYear", *FINANCIAL_COLUMNS}
    assert required.issubset(mapped.frame.columns)
    analyzed = analyze(mapped.frame, AnalysisConfig())
    assert len(analyzed) == 4


def test_beneish_matches_the_lecturer_reference_except_lvgi(mapped):
    """Seven of eight indices reproduce the lecturer's own numbers exactly.

    LVGI differs because the reference uses a liability definition that cannot
    be reconstructed from the published balance sheet. The formula is left as
    validated, so this records the known gap instead of hiding it.
    """
    analyzed = analyze(mapped.frame, AnalysisConfig()).set_index("FiscalYear")
    expected_2004 = {
        "DSRI": 1.2028213719637604, "GMI": 0.8898682184453459,
        "AQI": 1.322770532566582, "SGI": 1.0603429671258942,
        "DEPI": 1.1049695940929838, "SGAI": 1.0929758178502909,
        "TATA": 0.1302173612922029,
    }
    for name, value in expected_2004.items():
        assert analyzed.loc[2004, name] == pytest.approx(value, abs=1e-9)
    assert analyzed.loc[2004, "MScore"] == pytest.approx(-1.4577382242758077, abs=1e-9)


def test_first_year_has_no_comparison_basis(mapped):
    analyzed = analyze(mapped.frame, AnalysisConfig()).set_index("FiscalYear")
    assert pd.isna(analyzed.loc[2003, "MScore"])
    assert analyzed.loc[2003, "Status_178"] == "Insufficient data / not calculable"


def _population(rows: int = 40) -> pd.DataFrame:
    """A synthetic population with the eight index columns."""
    import numpy as np

    rng = np.random.default_rng(7)
    data = {name: rng.normal(1.0, 0.12, rows) for name in ("DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI")}
    data["TATA"] = rng.normal(0.0, 0.05, rows)
    return pd.DataFrame(data)


def test_population_is_used_for_fitting_but_not_returned(mapped):
    population = _population()
    scored, training_size = analyze_against_population(mapped.frame, population)
    assert training_size == len(population) + 3   # three calculable years
    assert len(scored) == len(mapped.frame)
    assert scored["Ticker"].unique().tolist() == ["TEST"]


def test_population_scoring_leaves_beneish_untouched(mapped):
    alone = analyze(mapped.frame, AnalysisConfig()).set_index("FiscalYear")
    scored, _ = analyze_against_population(mapped.frame, _population())
    scored = scored.set_index("FiscalYear")
    for year in (2004, 2005, 2006):
        assert scored.loc[year, "MScore"] == pytest.approx(alone.loc[year, "MScore"], abs=1e-12)
        assert scored.loc[year, "Status_178"] == alone.loc[year, "Status_178"]


def test_population_changes_the_anomaly_score(mapped):
    """Scores must shift once a reference population is supplied."""
    alone = analyze(mapped.frame, AnalysisConfig()).set_index("FiscalYear")
    scored, _ = analyze_against_population(mapped.frame, _population())
    scored = scored.set_index("FiscalYear")
    differences = [
        abs(scored.loc[year, "AnomalyScore"] - alone.loc[year, "AnomalyScore"])
        for year in (2004, 2005, 2006)
    ]
    assert max(differences) > 1e-6


def test_anomaly_conventions_are_preserved(mapped):
    scored, _ = analyze_against_population(mapped.frame, _population())
    labels = scored["AnomalyLabel"].dropna().unique().tolist()
    assert set(labels).issubset({1, -1})
    for _, row in scored.iterrows():
        if pd.isna(row["AnomalyLabel"]):
            assert row["AnomalyStatus"] == "Insufficient data / not calculable"
        elif row["AnomalyLabel"] == 1:
            assert row["AnomalyStatus"] == "Normal"
        else:
            assert row["AnomalyStatus"] == "Anomaly"


def test_empty_population_falls_back_to_the_upload_alone(mapped):
    scored, training_size = analyze_against_population(mapped.frame, pd.DataFrame())
    assert training_size == 3
    assert len(scored) == len(mapped.frame)


def test_mapping_reports_missing_accounts_instead_of_guessing(report):
    trimmed = report[report["Statement"].ne("Arus Kas")]
    result = map_report_to_financials(trimmed, ticker="TEST")
    assert "OperatingCashFlow" in result.unresolved
    assert not result.is_complete
