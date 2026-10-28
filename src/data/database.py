from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        values = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "name": os.getenv("DB_NAME", ""),
            "user": os.getenv("DB_USER", ""),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        if not values["name"] or not values["user"] or not values["password"]:
            raise ValueError("Database environment is incomplete")
        return cls(**values)


def create_mysql_engine(settings: DatabaseSettings | None = None) -> Engine:
    settings = settings or DatabaseSettings.from_environment()
    url = URL.create(
        "mysql+pymysql",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.name,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)
