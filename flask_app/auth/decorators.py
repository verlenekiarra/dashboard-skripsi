from __future__ import annotations

from functools import wraps

from flask import abort, redirect, session, url_for

from src.auth.permissions import allowed


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated_role"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("authenticated_role") not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def permission_required(operation: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get("authenticated_role")
            if not role:
                return redirect(url_for("auth.login"))
            if not allowed(role, operation):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
