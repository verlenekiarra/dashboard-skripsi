"""Login view. Credentials are verified server-side in src.auth.permissions."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.auth.permissions import authenticate, ensure_admin_user
from src.data.database import create_mysql_engine

# Typed.js-style loop (type, pause, delete, next) written locally: no CDN.
LOGIN_VISUAL = """
<div class="login-visual">
  <div class="login-kicker">Financial Risk Analytics</div>
  <h1 class="login-title"><span class="magic-title">Read the signal before the review </span></h1>
  <p class="login-copy">A focused workspace for Analyzing Indonesian Companies and Markets.</p>
  <p class="typed-line"><span id="typed-text">Screen financial risk before review.</span><span class="typed-caret" aria-hidden="true"></span></p>
</div>
<script>
(() => {
  const el = document.getElementById("typed-text");
  if (!el || el.dataset.started) return;
  el.dataset.started = "1";
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const lines = [
    ["Screen financial risk before review.", 70],
    ["Find unusual patterns earlier.", 45],
    ["Read company signals with context.", 60],
  ];
  let line = 0, pos = 0, deleting = false;
  const tick = () => {
    if (!document.body.contains(el)) return;
    const [text, speed] = lines[line];
    pos += deleting ? -1 : 1;
    el.textContent = text.slice(0, pos);
    let wait = deleting ? 35 : speed;
    if (!deleting && pos === text.length) { deleting = true; wait = 2000; }
    else if (deleting && pos === 0) { deleting = false; line = (line + 1) % lines.length; wait = 450; }
    setTimeout(tick, wait);
  };
  el.textContent = "";
  setTimeout(tick, 800);
})();
</script>
"""


def render_login() -> str | None:
    if st.session_state.get("authenticated_role"):
        return st.session_state["authenticated_role"]
    try:
        ensure_admin_user(create_mysql_engine())
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        pass
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    visual, form = st.columns([1.15, .85], gap="large")
    with visual:
        st.html(LOGIN_VISUAL, unsafe_allow_javascript=True)
    with form:
        st.markdown("### Sign in")
        st.caption("Access your financial screening workspace.")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width="stretch")
        st.caption(
            "Stakeholder or User access requests can be sent to verlenekiarra@gmail.com "
            "with a short explanation of the intended use."
        )
        if submitted:
            role = authenticate(username, password)
            if role:
                st.session_state["authenticated_role"] = role
                st.rerun()
            st.error("Invalid username or password.")
    st.markdown('</div>', unsafe_allow_html=True)
    return None
