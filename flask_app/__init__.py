from __future__ import annotations

import os

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "local-development-only"),
        DATABASE_URL=os.getenv("DATABASE_URL", ""),
    )

    from flask_app.auth.routes import auth_bp
    from flask_app.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    return app
