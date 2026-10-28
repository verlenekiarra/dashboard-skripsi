import os

import pytest
from sqlalchemy import inspect, text

from src.data.database import create_mysql_engine
from src.data.repository import read_analysis


pytestmark = pytest.mark.skipif(
    not all(os.getenv(name) for name in ("DB_NAME", "DB_USER", "DB_PASSWORD")),
    reason="MySQL integration environment is not configured",
)


def test_mysql_schema_and_relations():
    engine = create_mysql_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "dim_company", "dim_time", "fact_risk_analysis",
        "stg_financial_statement",
    }.issubset(tables)

    foreign_keys = inspector.get_foreign_keys("fact_risk_analysis")
    referred = {key["referred_table"] for key in foreign_keys}
    assert referred == {"dim_company", "dim_time"}


def test_mysql_data_has_no_duplicate_or_orphan_facts():
    engine = create_mysql_engine()
    with engine.connect() as connection:
        duplicate = connection.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT Company_ID, Time_ID
                FROM Fact_Risk_Analysis
                GROUP BY Company_ID, Time_ID
                HAVING COUNT(*) > 1
            ) duplicate_facts
        """)).scalar_one()
        orphan = connection.execute(text("""
            SELECT COUNT(*)
            FROM Fact_Risk_Analysis f
            LEFT JOIN Dim_Company c ON c.Company_ID = f.Company_ID
            LEFT JOIN Dim_Time t ON t.Time_ID = f.Time_ID
            WHERE c.Company_ID IS NULL OR t.Time_ID IS NULL
        """)).scalar_one()
    assert duplicate == 0
    assert orphan == 0


def test_mysql_analysis_can_feed_dashboard():
    frame = read_analysis(create_mysql_engine())
    assert not frame.empty
    assert {"Status_178", "Status_222", "AnomalyStatus", "RiskRank"}.issubset(frame.columns)
    assert sorted(frame["FiscalYear"].unique().tolist()) == [2023, 2024, 2025]
    assert frame["MScore"].notna().all()
