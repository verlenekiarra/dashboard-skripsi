from pathlib import Path

import pandas as pd
import pytest

from src.data.statement_report import period_change, read_statement_report, statement_matrix

REFERENCE = Path.home() / "Downloads" / "04b Kimia Farma.xlsx"
SHEET = "LK Kimia Farma"

pytestmark = pytest.mark.skipif(
    not REFERENCE.exists(),
    reason="Reference workbook is not available on this machine",
)


@pytest.fixture(scope="module")
def report() -> pd.DataFrame:
    return read_statement_report(REFERENCE, sheet_name=SHEET)


def test_all_three_statements_are_detected(report):
    assert sorted(report["Statement"].unique().tolist()) == ["Arus Kas", "Laba Rugi", "Neraca"]


def test_identity_and_periods_come_from_the_sheet(report):
    assert sorted(report["FiscalYear"].unique().tolist()) == [2003, 2004, 2005, 2006]
    assert "KIMIA FARMA" in report["Company"].dropna().iloc[0].upper()
    assert report["Unit"].dropna().iloc[0] == "juta Rupiah"


def test_reported_values_match_the_source(report):
    expected = {
        ("Neraca", "JUMLAH AKTIVA", 2006): 1261226,
        ("Neraca", "Jumlah Aktiva Lancar", 2003): 868926,
        ("Neraca", "JUMLAH KEWAJIBAN", 2004): 358855,
        ("Neraca", "JUMLAH KEWAJIBAN DAN EKUITAS", 2003): 1368146,
        ("Laba Rugi", "PENJUALAN BERSIH", 2006): 2189715,
        ("Laba Rugi", "LABA BERSIH", 2004): 77756,
        ("Laba Rugi", "LABA KOTOR", 2003): 542686,
        ("Arus Kas", "KAS DAN SETARA KAS AKHIR TAHUN", 2006): 210380,
    }
    for (statement, account, year), value in expected.items():
        row = report[
            report["Statement"].eq(statement)
            & report["AccountName"].eq(account)
            & report["FiscalYear"].eq(year)
        ]
        assert not row.empty, f"{statement} / {account} / {year} is missing"
        assert row["Value"].iloc[0] == value


def test_hierarchy_distinguishes_sections_totals_and_accounts(report):
    neraca = report[report["Statement"].eq("Neraca")]
    kinds = dict(zip(neraca["AccountName"], neraca["RowKind"]))
    assert kinds["AKTIVA"] == "section"
    assert kinds["Kas dan setara kas"] == "account"
    assert kinds["Jumlah Aktiva Lancar"] == "subtotal"
    assert kinds["JUMLAH AKTIVA"] == "total"


def test_section_headers_carry_no_values(report):
    sections = report[report["RowKind"].eq("section")]
    assert sections["Value"].isna().all()


def test_reported_zero_is_not_treated_as_missing(report):
    row = report[
        report["AccountName"].eq("Pinjaman dari pemerintah RI Jk. Pendek")
        & report["FiscalYear"].eq(2003)
    ]
    assert row["Value"].iloc[0] == 0.0
    assert row["Value"].notna().all()


def test_account_order_follows_the_source_sheet(report):
    neraca = report[report["Statement"].eq("Neraca")].drop_duplicates("RowOrder")
    order = neraca.sort_values("RowOrder")["AccountName"].tolist()
    assert order.index("AKTIVA LANCAR") < order.index("Kas dan setara kas")
    assert order.index("Kas dan setara kas") < order.index("Jumlah Aktiva Lancar")
    assert order.index("Jumlah Aktiva Lancar") < order.index("JUMLAH AKTIVA")


def test_matrix_puts_years_in_columns(report):
    matrix = statement_matrix(report, "Neraca", [2003, 2004, 2005, 2006])
    assert {"AccountName", "RowKind", "2003", "2006"}.issubset(matrix.columns)
    assert matrix.loc[matrix["AccountName"].eq("JUMLAH AKTIVA"), "2006"].iloc[0] == 1261226


def test_period_change_reports_nominal_and_percentage(report):
    change = period_change(report, "Neraca", 2005, 2006)
    cash = change[change["AccountName"].eq("Kas dan setara kas")].iloc[0]
    assert cash["Change"] == 210381 - 132865
    assert round(cash["ChangePercent"], 4) == round((210381 - 132865) / 132865 * 100, 4)


def test_percentage_is_empty_when_the_base_is_zero_or_missing(report):
    change = period_change(report, "Neraca", 2005, 2006)
    zero_base = change[change["AccountName"].eq("Kewajiban tidak lancar lainnya")]
    if not zero_base.empty:
        assert pd.isna(zero_base["ChangePercent"].iloc[0])
    sections = change[change["RowKind"].eq("section")]
    assert sections["ChangePercent"].isna().all()


def test_lecturer_ratio_block_is_excluded(report):
    accounts = report["AccountName"].str.upper().tolist()
    assert not any("RASIO BENEISH" in name for name in accounts)
    assert not any("M-SCORE" in name for name in accounts)
    assert not any("PERINGATAN" in name for name in accounts)


def test_unreadable_sheet_raises_a_clear_error(tmp_path):
    path = tmp_path / "plain.xlsx"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_excel(path, index=False)
    with pytest.raises(ValueError, match="No statement block found"):
        read_statement_report(path)
