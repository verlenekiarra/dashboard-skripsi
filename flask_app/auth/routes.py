from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from src.auth.permissions import authenticate

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = authenticate(request.form.get("username", ""), request.form.get("password", ""))
        if role:
            session["authenticated_role"] = role
            session["username"] = request.form.get("username", "").strip()
            return redirect(url_for("dashboard.overview"))
        flash("Username atau password tidak valid.", "error")
    return render_template("auth/login.html")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
