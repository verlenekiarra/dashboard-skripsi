from pathlib import Path


def test_mysql_schema_matches_metadata_contract():
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    expected = [
        "Company_ID INT UNSIGNED",
        "Ticker_Code VARCHAR(20)",
        "Company_Name VARCHAR(150)",
        "Fiscal_Year YEAR",
        "Total_Revenue DECIMAL(20,2)",
        "M_Score DECIMAL(12,6)",
        "Status_178 VARCHAR(50)",
        "Status_222 VARCHAR(50)",
        "Anomaly_Label TINYINT",
        "Anomaly_Score DECIMAL(12,8)",
        "PRIMARY KEY (Company_ID, Time_ID)",
        "FOREIGN KEY (Company_ID)",
        "FOREIGN KEY (Time_ID)",
    ]
    for definition in expected:
        assert definition in schema


def test_schema_contains_persistent_user_table():
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    for definition in [
        "CREATE TABLE IF NOT EXISTS App_Users",
        "Username VARCHAR(120)",
        "Password_Hash VARCHAR(255)",
        "Role ENUM('Administrator', 'Stakeholder', 'User')",
        "Is_Active BOOLEAN",
        "UNIQUE KEY uq_app_users_username",
    ]:
        assert definition in schema


def test_schema_is_non_destructive():
    schema = Path("sql/schema.sql").read_text(encoding="utf-8").upper()
    assert "DROP DATABASE" not in schema
    assert "DROP TABLE" not in schema
    assert "TRUNCATE" not in schema
