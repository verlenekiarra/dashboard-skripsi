"""Map a parsed statement report onto the 12 Beneish inputs.

This sits between src/data/statement_report.py (which reads a printed report)
and src/analytics/beneish.py (which scores it). The Beneish formula, the
thresholds, and the Isolation Forest configuration are not touched here; this
module only decides which reported account feeds which model input.

Account names vary between issuers, so each input carries a list of candidate
patterns. The first pattern that resolves wins, and anything unresolved is
reported rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from src.analytics.beneish import FINANCIAL_COLUMNS

# Candidate account names per Beneish input, most specific first.
# Each entry is (statement, regex) and the regex is matched case-insensitively
# against the reported account name.
ACCOUNT_PATTERNS: dict[str, tuple[tuple[str, str], ...]] = {
    "TotalRevenue": (
        ("Laba Rugi", r"^penjualan\s+bersih$"),
        ("Laba Rugi", r"^pendapatan\s+(bersih|usaha)$"),
        ("Laba Rugi", r"^(net\s+)?(sales|revenue)$"),
        ("Laba Rugi", r"\bpenjualan\s+neto\b"),
    ),
    "GrossProfit": (
        ("Laba Rugi", r"^laba\s+kotor$"),
        ("Laba Rugi", r"^gross\s+profit$"),
        ("Laba Rugi", r"\blaba\s+bruto\b"),
    ),
    "SellingGeneralAndAdministration": (
        ("Laba Rugi", r"^jumlah\s+beban\s+usaha$"),
        ("Laba Rugi", r"^total\s+beban\s+usaha$"),
        ("Laba Rugi", r"^beban\s+usaha$"),
        ("Laba Rugi", r"\bselling.*administrat"),
    ),
    "ReconciledDepreciation": (
        ("Laba Rugi", r"^depresiasi$"),
        ("Arus Kas", r"^(beban\s+)?(depresiasi|penyusutan)"),
        ("Laba Rugi", r"\b(depresiasi|penyusutan)\b"),
        ("Arus Kas", r"\bdepreciation\b"),
    ),
    "NetIncome": (
        ("Laba Rugi", r"^laba\s+bersih$"),
        ("Laba Rugi", r"^laba\s+\(rugi\)\s+bersih$"),
        ("Laba Rugi", r"^(net\s+income|net\s+profit)$"),
        ("Laba Rugi", r"\blaba\s+tahun\s+berjalan\b"),
    ),
    "AccountsReceivable": (
        ("Neraca", r"^piutang\s+usaha\s*-?\s*bersih$"),
        ("Neraca", r"^piutang\s+usaha$"),
        ("Neraca", r"^(trade\s+)?receivables?"),
        ("Neraca", r"\bpiutang\s+dagang\b"),
    ),
    "CurrentAssets": (
        ("Neraca", r"^jumlah\s+aktiva\s+lancar$"),
        ("Neraca", r"^(jumlah|total)\s+aset\s+lancar$"),
        ("Neraca", r"^total\s+current\s+assets$"),
    ),
    "NetPPE": (
        ("Neraca", r"^aktiva\s+tetap\s*-?\s*bersih$"),
        ("Neraca", r"^aset\s+tetap\s*-?\s*(bersih|neto)$"),
        ("Neraca", r"^(net\s+)?(property|fixed\s+assets)"),
    ),
    "TotalAssets": (
        ("Neraca", r"^jumlah\s+aktiva$"),
        ("Neraca", r"^(jumlah|total)\s+aset$"),
        ("Neraca", r"^total\s+assets$"),
    ),
    "CurrentLiabilities": (
        ("Neraca", r"^jumlah\s+kewajiban\s+lancar$"),
        ("Neraca", r"^(jumlah|total)\s+liabilitas\s+jangka\s+pendek$"),
        ("Neraca", r"^total\s+current\s+liabilities$"),
    ),
    "LongTermDebt": (
        ("Neraca", r"^jumlah\s+kewajiban\s+tidak\s+lancar$"),
        ("Neraca", r"^(jumlah|total)\s+liabilitas\s+jangka\s+panjang$"),
        ("Neraca", r"^total\s+non-?current\s+liabilities$"),
    ),
    "OperatingCashFlow": (
        ("Arus Kas", r"^kas\s+bersih\s+dari\s+\(untuk\)\s+akt\.?\s+operasi$"),
        ("Arus Kas", r"kas\s+(bersih|neto).*aktivitas\s+operasi"),
        ("Arus Kas", r"^net\s+cash.*operating\s+activities"),
    ),
}

DEFAULT_SECTOR = "Manufacturing"


@dataclass(frozen=True)
class MappingResult:
    """The mapped frame plus a record of how each input was resolved."""

    frame: pd.DataFrame
    resolved: dict[str, str]
    unresolved: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.unresolved


def _find_account(report: pd.DataFrame, statement: str, pattern: str) -> pd.Series | None:
    """Values by year for the first account matching `pattern`, or None."""
    subset = report[report["Statement"].eq(statement)]
    if subset.empty:
        return None
    matches = subset[subset["AccountName"].str.strip().str.match(pattern, case=False, na=False)]
    if matches.empty:
        matches = subset[subset["AccountName"].str.strip().str.contains(pattern, case=False, na=False, regex=True)]
    if matches.empty:
        return None
    # Prefer the earliest reported row so a subtotal beats a later restatement.
    chosen = matches.sort_values("RowOrder")["RowOrder"].iloc[0]
    rows = matches[matches["RowOrder"].eq(chosen)]
    values = rows.set_index("FiscalYear")["Value"]
    if values.isna().all():
        return None
    return values


def map_report_to_financials(
    report: pd.DataFrame,
    ticker: str,
    company_name: str = "",
    sector: str = DEFAULT_SECTOR,
) -> MappingResult:
    """Build a Beneish-ready frame from a parsed statement report."""
    if report.empty:
        raise ValueError("Statement report is empty")

    years = sorted(int(year) for year in report["FiscalYear"].unique())
    if not company_name:
        candidates = [c for c in report["Company"].dropna().unique().tolist() if str(c).strip()]
        company_name = candidates[0] if candidates else ticker

    columns: dict[str, list] = {
        "Ticker": [ticker] * len(years),
        "CompanyName": [company_name] * len(years),
        "Sector": [sector] * len(years),
        "FiscalYear": years,
    }

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for column in FINANCIAL_COLUMNS:
        patterns = ACCOUNT_PATTERNS.get(column, ())
        series: pd.Series | None = None
        source = ""
        for statement, pattern in patterns:
            series = _find_account(report, statement, pattern)
            if series is not None:
                matched = report[
                    report["Statement"].eq(statement)
                    & report["AccountName"].str.strip().str.contains(pattern, case=False, na=False, regex=True)
                ]
                label = matched.sort_values("RowOrder")["AccountName"].iloc[0] if not matched.empty else pattern
                source = f"{statement} / {label.strip()}"
                break
        if series is None:
            columns[column] = [None] * len(years)
            unresolved.append(column)
            continue
        columns[column] = [series.get(year) for year in years]
        resolved[column] = source

    frame = pd.DataFrame(columns)
    for column in FINANCIAL_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return MappingResult(frame=frame, resolved=resolved, unresolved=tuple(unresolved))
