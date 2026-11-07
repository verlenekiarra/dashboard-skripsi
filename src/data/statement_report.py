"""Parser for financial statement workbooks laid out as printed reports.

This is a different shape from src/data/io.py. That module reads tabular
uploads (Ticker, Year, Item, Value) meant for the Beneish pipeline. A printed
report instead carries title rows, a year header row, blank spacer rows,
account hierarchy, and subtotal lines, and a single sheet may hold several
statements one after another.

Nothing here touches the Beneish or Isolation Forest inputs. The output is for
reading the statement as published, not for scoring it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

# A statement starts at a row whose text matches one of these.
STATEMENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bNERACA\b", "Neraca"),
    (r"\bLAPORAN\s+LABA\s+RUGI\b", "Laba Rugi"),
    (r"\bLABA\s+RUGI\b", "Laba Rugi"),
    (r"\bLAPORAN\s+ARUS\s+KAS\b", "Arus Kas"),
    (r"\bARUS\s+KAS\b", "Arus Kas"),
    (r"\bBALANCE\s+SHEET\b", "Neraca"),
    (r"\bINCOME\s+STATEMENT\b", "Laba Rugi"),
    (r"\bCASH\s+FLOW\b", "Arus Kas"),
)

UNIT_PATTERN = re.compile(r"disajikan\s+dalam\s+(.+?)\s*\)?$", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"^(19|20)\d{2}$")

# Rows past this marker belong to the lecturer's own scratch calculations,
# not to the published statement.
TRAILING_MARKERS = (r"\bRASIO\b", r"\bM-?SCORE\b", r"\bPERINGATAN\b", r"\bKOEFISIEN\b")

SUBTOTAL_PATTERN = re.compile(r"^\s*(jumlah|total|sub\s*total)\b", re.IGNORECASE)

ROW_SECTION = "section"
ROW_SUBHEADER = "subheader"
ROW_ACCOUNT = "account"
ROW_SUBTOTAL = "subtotal"
ROW_TOTAL = "total"


@dataclass(frozen=True)
class StatementBlock:
    """One statement found inside a sheet."""

    statement: str
    title: str
    company: str
    period: str
    unit: str
    years: tuple[int, ...]
    start_row: int
    end_row: int


def _as_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if pd.isna(value):
        return ""
    return str(value)


def _row_label(row: pd.Series) -> str:
    """The account or title text of a row: its first non-empty cell."""
    for value in row.tolist():
        text = _as_text(value)
        if text.strip():
            return text
    return ""


def _numeric_cells(row: pd.Series) -> list[float | None]:
    values: list[float | None] = []
    for value in row.tolist():
        if value is None or pd.isna(value):
            values.append(None)
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
            continue
        cleaned = _as_text(value).strip().replace(",", "")
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        try:
            values.append(float(cleaned))
        except ValueError:
            values.append(None)
    return values


def _match_statement(label: str) -> str | None:
    upper = label.upper()
    for pattern, name in STATEMENT_PATTERNS:
        if re.search(pattern, upper):
            return name
    return None


def _is_trailing_marker(label: str) -> bool:
    upper = label.upper()
    return any(re.search(pattern, upper) for pattern in TRAILING_MARKERS)


def _has_year_header_ahead(frame: pd.DataFrame, row_index: int, lookahead: int = 8) -> bool:
    """True when a fiscal-year header row follows, with only text rows between.

    This separates a statement title from a section heading inside one. Both
    can read as "ARUS KAS ...", but a real title is followed by title and unit
    text and then the year header, while a section heading is followed straight
    away by account rows carrying numbers.
    """
    for forward in range(row_index + 1, min(row_index + 1 + lookahead, len(frame))):
        row = frame.iloc[forward]
        if _year_columns(row):
            return True
        if any(value is not None for value in _numeric_cells(row)):
            return False
    return False


def _year_columns(row: pd.Series) -> dict[int, int]:
    """Map column index to fiscal year for a header row, or {} if not one."""
    found: dict[int, int] = {}
    for column, value in enumerate(row.tolist()):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value):
            candidate = int(value)
            if 1900 <= candidate <= 2100 and float(value) == candidate:
                found[column] = candidate
                continue
        text = _as_text(value).strip()
        if YEAR_PATTERN.match(text):
            found[column] = int(text)
    return found if len(found) >= 2 else {}


def _classify(label: str, has_values: bool) -> tuple[str, int]:
    """Decide the row kind and indent level from the label text.

    Indentation in the source is leading whitespace, not an Excel indent
    attribute, so the level is read from the raw string.
    """
    stripped = label.strip()
    leading = len(label) - len(label.lstrip())
    level = 1 if leading >= 3 else 0

    if SUBTOTAL_PATTERN.match(stripped):
        letters = [c for c in stripped if c.isalpha()]
        is_shouted = bool(letters) and all(c.isupper() for c in letters)
        return (ROW_TOTAL if is_shouted else ROW_SUBTOTAL), level

    if not has_values:
        letters = [c for c in stripped if c.isalpha()]
        is_shouted = bool(letters) and all(c.isupper() for c in letters)
        return (ROW_SECTION if is_shouted and level == 0 else ROW_SUBHEADER), level

    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return ROW_TOTAL, level

    return ROW_ACCOUNT, level


def _find_blocks(frame: pd.DataFrame) -> list[StatementBlock]:
    blocks: list[StatementBlock] = []
    starts: list[tuple[int, str, str]] = []

    for index in range(len(frame)):
        label = _row_label(frame.iloc[index])
        if not label.strip():
            continue
        if _is_trailing_marker(label):
            break
        statement = _match_statement(label)
        # A section heading inside a statement can read like a title
        # ("ARUS KAS DARI AKTIVITAS OPERASI"). Only a real title is followed
        # by the fiscal-year header row.
        if statement and _has_year_header_ahead(frame, index):
            starts.append((index, statement, label.strip()))

    cutoff = len(frame)
    for index in range(len(frame)):
        if _is_trailing_marker(_row_label(frame.iloc[index])):
            cutoff = index
            break

    starts = [s for s in starts if s[0] < cutoff]

    for position, (row_index, statement, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else cutoff

        company = ""
        for back in range(row_index - 1, max(row_index - 6, -1), -1):
            candidate = _row_label(frame.iloc[back]).strip()
            if candidate and not _match_statement(candidate):
                company = candidate
            else:
                break

        unit = ""
        period = ""
        years: dict[int, int] = {}
        header_row = row_index
        for forward in range(row_index + 1, min(row_index + 8, end)):
            row = frame.iloc[forward]
            label = _row_label(row).strip()
            mapping = _year_columns(row)
            if mapping and not label:
                years = mapping
                header_row = forward
                break
            if mapping and label and _year_columns(row):
                years = mapping
                header_row = forward
                break
            match = UNIT_PATTERN.search(label)
            if match:
                unit = match.group(1).strip().rstrip(")").strip()
            elif label and not period:
                period = label

        if not years:
            continue

        blocks.append(StatementBlock(
            statement=statement,
            title=title,
            company=company,
            period=period,
            unit=unit,
            years=tuple(years[column] for column in sorted(years)),
            start_row=header_row + 1,
            end_row=end,
        ))

    return blocks


def read_statement_report(path_or_buffer, sheet_name=0) -> pd.DataFrame:
    """Read a printed-report sheet into long form.

    Returns columns: Statement, Company, Unit, Period, AccountName, Level,
    RowKind, RowOrder, FiscalYear, Value. Value is NA for a blank cell and 0.0
    for a reported zero; the two are never merged.
    """
    frame = pd.read_excel(path_or_buffer, sheet_name=sheet_name, header=None)
    if frame.empty:
        raise ValueError("Sheet is empty")

    blocks = _find_blocks(frame)
    if not blocks:
        raise ValueError(
            "No statement block found. Expected a title row such as "
            "'NERACA KONSOLIDASI' followed by a row of fiscal years."
        )

    header_years: dict[str, dict[int, int]] = {}
    for block in blocks:
        row = frame.iloc[block.start_row - 1]
        header_years[block.title] = _year_columns(row)

    records: list[dict] = []
    for block in blocks:
        columns = header_years[block.title]
        order = 0
        for index in range(block.start_row, block.end_row):
            row = frame.iloc[index]
            label = _row_label(row)
            if not label.strip():
                continue
            if _is_trailing_marker(label):
                break

            numbers = _numeric_cells(row)
            has_values = any(
                numbers[column] is not None
                for column in columns
                if column < len(numbers)
            )
            row_kind, level = _classify(label, has_values)
            order += 1

            for column, year in sorted(columns.items()):
                value = numbers[column] if column < len(numbers) else None
                records.append({
                    "Statement": block.statement,
                    "StatementTitle": block.title,
                    "Company": block.company,
                    "Unit": block.unit,
                    "Period": block.period,
                    "AccountName": label.strip(),
                    "Level": level,
                    "RowKind": row_kind,
                    "RowOrder": order,
                    "FiscalYear": year,
                    "Value": value,
                })

    result = pd.DataFrame.from_records(records)
    if result.empty:
        raise ValueError("Statement block found but it holds no account rows")
    result["Value"] = pd.to_numeric(result["Value"], errors="coerce")
    result["FiscalYear"] = result["FiscalYear"].astype(int)
    return result


def statement_matrix(data: pd.DataFrame, statement: str, years: list[int]) -> pd.DataFrame:
    """Pivot one statement into accounts as rows and years as columns.

    Account order and hierarchy follow the source sheet.
    """
    subset = data[data["Statement"].eq(statement) & data["FiscalYear"].isin(years)]
    if subset.empty:
        return pd.DataFrame()

    layout = (
        subset[["RowOrder", "AccountName", "Level", "RowKind"]]
        .drop_duplicates("RowOrder")
        .sort_values("RowOrder")
    )
    wide = subset.pivot_table(
        index="RowOrder", columns="FiscalYear", values="Value", aggfunc="first", dropna=False
    )
    merged = layout.set_index("RowOrder").join(wide).reset_index(drop=True)
    merged.columns = [str(c) for c in merged.columns]
    return merged


def period_change(data: pd.DataFrame, statement: str, base_year: int, compare_year: int) -> pd.DataFrame:
    """Nominal and percentage change between two periods.

    Percentage is left empty when the base is missing or zero; dividing by zero
    is not reported as 0 or infinity.
    """
    subset = data[data["Statement"].eq(statement) & data["FiscalYear"].isin([base_year, compare_year])]
    if subset.empty:
        return pd.DataFrame()

    layout = (
        subset[["RowOrder", "AccountName", "Level", "RowKind"]]
        .drop_duplicates("RowOrder")
        .sort_values("RowOrder")
    )
    wide = subset.pivot_table(
        index="RowOrder", columns="FiscalYear", values="Value", aggfunc="first", dropna=False
    )
    merged = layout.set_index("RowOrder").join(wide)

    base = merged.get(base_year)
    compare = merged.get(compare_year)
    if base is None or compare is None:
        return pd.DataFrame()

    merged["Change"] = compare - base
    safe_base = base.where(base.notna() & base.ne(0))
    merged["ChangePercent"] = (compare - base) / safe_base.abs() * 100

    merged = merged.rename(columns={base_year: f"{base_year}", compare_year: f"{compare_year}"})
    return merged.reset_index(drop=True)
