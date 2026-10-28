from __future__ import annotations

import hashlib
import hmac
import json
import os


def authenticate(username: str, password: str) -> str | None:
    raw_users = os.getenv("APP_USERS_JSON", "")
    if not raw_users:
        return None
    try:
        users = json.loads(raw_users)
    except json.JSONDecodeError:
        return None
    record = users.get(username)
    if not isinstance(record, dict) or not verify_password(password, record.get("password_hash", "")):
        return None
    role = record.get("role")
    return role if role in {"Administrator", "Stakeholder", "User"} else None


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def allowed(role: str, operation: str) -> bool:
    permissions = {
        "Administrator": {"view", "upload", "analyze", "export", "manage_accounts", "manage_system"},
        "Stakeholder": {"view", "upload", "analyze", "export"},
        "User": {"view"},
    }
    return operation in permissions.get(role, set())
