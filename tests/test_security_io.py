import io

import pandas as pd
import pytest

from src.auth.permissions import allowed, ensure_admin_user, hash_password, verify_password
from src.data.io import read_upload


def test_role_permissions():
    assert allowed("Administrator", "manage_system")
    assert allowed("Stakeholder", "upload")
    assert allowed("Stakeholder", "export")
    assert not allowed("User", "upload")
    assert not allowed("User", "export")


def test_password_hash_verification():
    encoded = hash_password("example-password")
    assert verify_password("example-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_admin_bootstrap_is_importable():
    assert callable(ensure_admin_user)


def test_upload_rejects_missing_schema():
    uploaded = io.BytesIO(b"Ticker,FiscalYear\nCPIN.JK,2023\n")
    uploaded.name = "data.csv"
    with pytest.raises(ValueError, match="Missing required columns"):
        read_upload(uploaded)
