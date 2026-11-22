import io

import pandas as pd
import pytest

from flask_app import create_app
from flask_app.auth import routes as auth_routes
from flask_app.dashboard import routes
from src.auth.permissions import hash_password


@pytest.fixture
def client(monkeypatch):
    users = {"viewer": {"password_hash": hash_password("secret"), "role": "User"},
             "admin": {"password_hash": hash_password("secret"), "role": "Administrator"}}
    monkeypatch.setenv("APP_USERS_JSON", __import__("json").dumps(users))
    monkeypatch.setattr(auth_routes, "authenticate", lambda username, password: users.get(username, {}).get("role") if users.get(username, {}).get("password_hash") and username in users and password == "secret" else None)
    monkeypatch.setattr(routes, "create_mysql_engine", lambda: (_ for _ in ()).throw(RuntimeError("no DB")))
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test")
    return app.test_client()


def login(client, username="viewer"):
    return client.post("/login", data={"username": username, "password": "secret"}, follow_redirects=True)


def test_login_and_session_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"No observations available" in response.data


def test_anonymous_redirects_to_login(client):
    response = client.get("/beneish")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_cannot_access_admin(client):
    login(client)
    assert client.get("/data-management").status_code == 403
    assert client.get("/user-management").status_code == 403


def test_admin_page_requires_admin_database(client):
    login(client, "admin")
    response = client.get("/user-management")
    assert response.status_code == 200
    assert b"Data unavailable" in response.data


def test_export_parity(client, monkeypatch):
    login(client, "admin")
    frame = pd.DataFrame({"Ticker": ["ABC"], "FiscalYear": [2023]})
    monkeypatch.setattr(routes, "_data", lambda: (frame, ""))
    csv_response = client.get("/export/csv")
    assert csv_response.status_code == 200
    assert b"Ticker,FiscalYear" in csv_response.data
    excel_response = client.get("/export/xlsx")
    assert excel_response.status_code == 200
    assert excel_response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_upload_reuses_legacy_parser(client, monkeypatch):
    login(client, "admin")
    frame = pd.DataFrame({
        "Ticker": ["ABC", "ABC"], "CompanyName": ["ABC", "ABC"], "Sector": ["Manufacturing"] * 2,
        "FiscalYear": [2022, 2023], "TotalRevenue": [100, 110], "GrossProfit": [20, 22],
        "SellingGeneralAndAdministration": [5, 6], "ReconciledDepreciation": [2, 2],
        "NetIncome": [5, 6], "AccountsReceivable": [10, 12], "CurrentAssets": [30, 32],
        "NetPPE": [40, 41], "TotalAssets": [70, 73], "CurrentLiabilities": [10, 11],
        "LongTermDebt": [5, 5], "OperatingCashFlow": [6, 7],
    })
    monkeypatch.setattr(routes, "read_upload", lambda uploaded: frame)
    monkeypatch.setattr(routes, "create_mysql_engine", lambda: object())
    monkeypatch.setattr(routes, "load_analysis", lambda engine, analyzed: len(analyzed))
    response = client.post("/upload", data={"file": (io.BytesIO(b"unused"), "data.csv"), "confirmed": "yes"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"observasi tersimpan" in response.data
