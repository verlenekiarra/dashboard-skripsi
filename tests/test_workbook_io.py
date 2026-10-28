from io import BytesIO
from pathlib import Path

from src.data.io import read_upload, read_validated_analysis_workbook


def test_raw_workbook_maps_to_analytic_shape():
    path = Path(".agents/skills/docs/skripsi_rawwwwwwwww_ajajaja.xlsx")
    uploaded = BytesIO(path.read_bytes())
    uploaded.name = path.name
    frame = read_upload(uploaded)
    assert len(frame) == 1321
    assert frame["Ticker"].nunique() == 321
    assert frame.duplicated(["Ticker", "FiscalYear"]).sum() == 0
    assert {"TotalRevenue", "TotalAssets", "OperatingCashFlow"}.issubset(frame.columns)


def test_validated_workbook_maps_to_fact_shape():
    path = Path(".agents/skills/docs/beneish_anomaly_finallll_full.xlsx")
    frame = read_validated_analysis_workbook(path)
    assert len(frame) == 629
    assert sorted(frame["FiscalYear"].unique().tolist()) == [2023, 2024, 2025]
    assert frame["MScore"].notna().all()
    assert frame["AnomalyLabel"].notna().all()
    assert int(frame["Status_178"].eq("Potential earnings manipulation").sum()) == 112
    assert int(frame["Status_222"].eq("Potential earnings manipulation").sum()) == 207
