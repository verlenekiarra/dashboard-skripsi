from __future__ import annotations

import hashlib
import hmac
import json
import os

from sqlalchemy import text


VALID_ROLES = {"Administrator", "Stakeholder", "User"}


def _authenticate_json(username: str, password: str) -> str | None:
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
    return role if role in VALID_ROLES else None


def authenticate(username: str, password: str) -> str | None:
    """Authenticate against MySQL users, with local JSON fallback."""
    try:
        from src.data.database import create_mysql_engine

        engine = create_mysql_engine()
        with engine.connect() as connection:
            record = connection.execute(
                text("""
                    SELECT password_hash AS "Password_Hash", role AS "Role"
                    FROM App_Users
                    WHERE Username = :username AND Is_Active = TRUE
                """),
                {"username": username.strip()},
            ).mappings().first()
        if record and verify_password(password, record["Password_Hash"]):
            return record["Role"] if record["Role"] in VALID_ROLES else None
        return None
    except Exception:
        return _authenticate_json(username, password)


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


def ensure_admin_user(engine) -> bool:
    """Create default admin only when no admin account exists."""
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS App_Users (
                User_ID BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                Username VARCHAR(120) NOT NULL,
                Password_Hash VARCHAR(255) NOT NULL,
                Role ENUM('Administrator', 'Stakeholder', 'User') NOT NULL,
                Is_Active BOOLEAN NOT NULL DEFAULT TRUE,
                Created_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                Updated_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (User_ID),
                UNIQUE KEY uq_app_users_username (Username)
            ) ENGINE=InnoDB
        """))
        exists = connection.execute(text("""
            SELECT 1 FROM App_Users
            WHERE Username = 'admin' AND Role = 'Administrator'
            LIMIT 1
        """)).scalar()
        if exists:
            return False
        connection.execute(text("""
            INSERT INTO App_Users (Username, Password_Hash, Role)
            VALUES ('admin', :password_hash, 'Administrator')
        """), {"password_hash": hash_password("admin123")})
        return True


def create_user(engine, username: str, password: str, role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError("Role tidak valid.")
    if not username.strip() or not password:
        raise ValueError("Username dan password wajib diisi.")
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO App_Users (Username, Password_Hash, Role)
            VALUES (:username, :password_hash, :role)
        """), {
            "username": username.strip(),
            "password_hash": hash_password(password),
            "role": role,
        })


def list_users(engine):
    with engine.connect() as connection:
        return connection.execute(text("""
            SELECT User_ID, Username, Role, Is_Active, Created_At, Updated_At
            FROM App_Users
            ORDER BY Username
        """)).mappings().all()


def update_user(engine, user_id: int, role: str, password: str = "") -> None:
    if role not in VALID_ROLES:
        raise ValueError("Role tidak valid.")
    values = {"user_id": user_id, "role": role}
    password_clause = ""
    if password:
        password_clause = ", Password_Hash = :password_hash"
        values["password_hash"] = hash_password(password)
    with engine.begin() as connection:
        connection.execute(text(f"""
            UPDATE App_Users
            SET Role = :role{password_clause}
            WHERE User_ID = :user_id
        """), values)


def set_user_active(engine, user_id: int, active: bool) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            UPDATE App_Users
            SET Is_Active = :active
            WHERE User_ID = :user_id
        """), {"active": active, "user_id": user_id})
