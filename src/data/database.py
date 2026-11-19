from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

# Supabase branch uses .env.supabase locally; Streamlit Cloud uses st.secrets.
load_dotenv(".env.supabase", override=False)
load_dotenv(".env", override=False)


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        secret_values = {}
        try:
            import streamlit as st
            secret_values = dict(st.secrets)
        except Exception:
            pass

        def value(name: str, default: str = "") -> str:
            return os.getenv(name, secret_values.get(name, default))

        values = {
            "host": value("DB_HOST", "127.0.0.1"),
            "port": int(value("DB_PORT", "3306")),
            "name": value("DB_NAME"),
            "user": value("DB_USER"),
            "password": value("DB_PASSWORD"),
        }
        if not values["name"] or not values["user"] or not values["password"]:
            raise ValueError("Database environment is incomplete")
        return cls(**values)


def create_mysql_engine(settings: DatabaseSettings | None = None) -> Engine:
    settings = settings or DatabaseSettings.from_environment()
    driver = os.getenv("DB_DRIVER", "postgresql+psycopg2")
    url = URL.create(
        driver,
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.name,
        query={"charset": "utf8mb4"} if driver == "mysql+pymysql" else {"sslmode": "require"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)
