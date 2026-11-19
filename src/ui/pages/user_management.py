from __future__ import annotations

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.auth.permissions import allowed, create_user
from src.data.database import create_mysql_engine
from src.ui.config import ROLE_OPTIONS


def render_user_management(role: str) -> None:
    st.markdown("### User Management")
    if not allowed(role, "manage_accounts"):
        st.error("Akses ditolak. Hanya Administrator dapat mengelola akun.")
        return
    from src.auth.permissions import hash_password
    st.caption("Daftarkan akun baru beserta rolenya. Password disimpan sebagai hash PBKDF2.")
    with st.form("create_user"):
        username = st.text_input("Username")
        new_role = st.selectbox("Role", ROLE_OPTIONS, index=2)
        password = st.text_input("Password sementara", type="password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if not username or not password:
            st.error("Username dan password wajib diisi.")
            return
        try:
            create_user(create_mysql_engine(), username, password, new_role)
            st.success(f"Akun {username} tersimpan sebagai {new_role}.")
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Akun gagal disimpan: {exc}")
    st.markdown('<p class="section-title">Existing accounts</p>', unsafe_allow_html=True)
    try:
        engine = create_mysql_engine()
        with engine.connect() as connection:
            users = connection.execute(text("""
                SELECT user_id AS "User_ID", username AS "Username", role AS "Role", is_active AS "Is_Active"
                FROM App_Users
                WHERE username <> 'admin'
                ORDER BY username
            """)).mappings().all()
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        st.error(f"Daftar akun gagal dimuat: {exc}")
        return

    if not users:
        st.info("Belum ada akun selain admin. Buat akun baru pada form di atas.")
        return

    accounts = {user["Username"]: user for user in users}
    selected_username = st.selectbox("Pilih username", list(accounts.keys()))
    account = accounts[selected_username]
    user_id = int(account["User_ID"])
    current_role = account["Role"]
    active = bool(account["Is_Active"])

    info_username, info_role, info_status = st.columns(3)
    info_username.metric("Username", selected_username)
    info_role.metric("Role", current_role)
    info_status.metric("Status", "Active" if active else "Inactive")

    with st.form(f"edit_user_{user_id}"):
        edited_role = st.segmented_control("Ubah role", ROLE_OPTIONS, default=current_role, key=f"role_{user_id}")
        reset_password = st.text_input("Password baru (opsional)", type="password", key=f"password_{user_id}")
        save = st.form_submit_button("Save changes")
    if save:
        try:
            values = {"user_id": user_id, "role": edited_role or current_role}
            password_clause = ""
            if reset_password:
                password_clause = ", Password_Hash = :password_hash"
                values["password_hash"] = hash_password(reset_password)
            with engine.begin() as connection:
                connection.execute(text(f"""
                    UPDATE App_Users
                    SET Role = :role{password_clause}
                    WHERE User_ID = :user_id AND Username = :username
                """), {**values, "username": selected_username})
            st.success(f"Akun {selected_username} diperbarui.")
            st.rerun()
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Akun gagal diperbarui: {exc}")

    action = "Enable account" if not active else "Disable account"
    if st.button(action, key=f"active_{user_id}"):
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE App_Users
                SET Is_Active = :active
                WHERE User_ID = :user_id AND Username = :username
            """), {"active": not active, "user_id": user_id, "username": selected_username})
        st.rerun()

    confirm_delete = st.checkbox(f"Konfirmasi hapus permanen akun {selected_username}", key=f"confirm_delete_{user_id}")
    if st.button("Delete user", key=f"delete_{user_id}", disabled=not confirm_delete):
        try:
            with engine.begin() as connection:
                connection.execute(text("""
                    DELETE FROM App_Users
                    WHERE User_ID = :user_id AND Username = :username
                """), {"user_id": user_id, "username": selected_username})
            st.success(f"Akun {selected_username} dihapus.")
            st.rerun()
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Akun belum dapat dihapus. Hak DELETE database belum tersedia: {exc}")
    st.caption("Disable menutup akses tetapi data akun tetap ada. Delete menghapus akun permanen dan tidak bisa dibatalkan.")
