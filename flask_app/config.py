from __future__ import annotations

import os


def flask_config() -> dict[str, str]:
    return {
        "SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "local-development-only"),
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
    }
