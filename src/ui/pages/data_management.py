from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.auth.permissions import allowed
from src.analytics.beneish import BASELINE_THRESHOLD, SENSITIVITY_THRESHOLD
from src.data.database import create_mysql_engine


FACT_RESULT_COLUMNS = {
    "DSRI": "DSRI",
    "GMI": "GMI",
    "AQI": "AQI",
    "SGI": "SGI",
    "DEPI": "DEPI",
    "SGAI": "SGAI",
    "LVGI": "LVGI",
    "TATA": "TATA",
    "M-Score": "M_Score",
    "Anomaly Score": "Anomaly_Score",
}


def _rows(engine) -> pd.DataFrame:
    query = text("""
        SELECT c.Ticker_Code AS Ticker, c.Company_Name AS CompanyName,
               c.Sector, t.Fiscal_Year AS FiscalYear,
               f.DSRI, f.GMI, f.AQI, f.SGI, f.DEPI, f.SGAI, f.LVGI, f.TATA,
               f.M_Score AS MScore, f.Status_178 AS RiskLabel,
               f.Anomaly_Label AS AnomalyLabel, f.Anomaly_Score AS AnomalyScore
        FROM Fact_Risk_Analysis f
        JOIN Dim_Company c ON c.Company_ID = f.Company_ID
        JOIN Dim_Time t ON t.Time_ID = f.Time_ID
        ORDER BY c.Ticker_Code, t.Fiscal_Year
    """)
    return pd.read_sql(query, engine)


def _delete_fact_record(engine, ticker: str, year: int) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            DELETE f FROM Fact_Risk_Analysis f
            JOIN Dim_Company c ON c.Company_ID = f.Company_ID
            JOIN Dim_Time t ON t.Time_ID = f.Time_ID
            WHERE c.Ticker_Code = :ticker AND t.Fiscal_Year = :year
        """), {"ticker": ticker, "year": year})


def _delete_fact_dialog(engine, ticker: str, year: int) -> None:
    @st.dialog("Konfirmasi delete")
    def confirm():
        st.warning(f"Hapus hasil Fact_Risk_Analysis untuk {ticker} tahun {year}?")
        st.caption("Raw staging tetap tersimpan.")
        left, right = st.columns(2)
        if left.button("Cancel", key="cancel_fact_delete"):
            st.rerun()
        if right.button("Yes, delete", key="confirm_fact_delete_dialog"):
            _delete_fact_record(engine, ticker, year)
            st.success("Hasil fact dihapus.")
            st.rerun()
    confirm()


def render_data_management(data: pd.DataFrame, role: str) -> None:
    st.markdown("### Data Management")
    if not allowed(role, "manage_system"):
        st.error("Akses ditolak. Data Management hanya untuk Administrator.")
        return
    st.caption("Pengelolaan data perusahaan dan company-year. Perubahan database memerlukan konfirmasi.")
    try:
        engine = create_mysql_engine()
        rows = _rows(engine)
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        st.error(f"Data gagal dimuat: {exc}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Companies", f"{rows['Ticker'].nunique():,}")
    c2.metric("Observations", f"{len(rows):,}")
    c3.metric("Incomplete M-Score", f"{rows['MScore'].isna().sum():,}")

    st.markdown('<p class="section-title">Company-year data</p>', unsafe_allow_html=True)
    if rows.empty:
        st.info("Belum ada company-year data.")
        return
    selected = st.selectbox(
        "Pilih ticker dan tahun",
        rows.index,
        format_func=lambda i: f"{rows.loc[i, 'Ticker']} · {rows.loc[i, 'CompanyName']} · {int(rows.loc[i, 'FiscalYear'])}",
        key="data_fact_row",
    )
    selected_ticker = str(rows.loc[selected, "Ticker"])
    selected_year = int(rows.loc[selected, "FiscalYear"])

    st.caption(f"Company: {rows.loc[selected, 'CompanyName']}")
    result_label = st.selectbox("Pilih kolom hasil analisis", list(FACT_RESULT_COLUMNS), key="fact_result_column")
    database_column = FACT_RESULT_COLUMNS[result_label]
    current_value = rows.loc[selected, "MScore" if result_label == "M-Score" else "AnomalyScore" if result_label == "Anomaly Score" else result_label]
    default_value = 0.0 if pd.isna(current_value) else float(current_value)
    new_value = st.number_input("Nilai baru", value=default_value, format="%.8f", key="fact_new_value")
    confirm_update = st.checkbox("Konfirmasi update nilai hasil analisis", key="confirm_fact_update")
    with st.form("update_fact_result"):
        update_result = st.form_submit_button("Update analysis result", disabled=not confirm_update)
    if update_result:
        try:
            with engine.begin() as connection:
                connection.execute(text(f"""
                    UPDATE Fact_Risk_Analysis f
                    JOIN Dim_Company c ON c.Company_ID = f.Company_ID
                    JOIN Dim_Time t ON t.Time_ID = f.Time_ID
                    SET f.{database_column} = :value
                    WHERE c.Ticker_Code = :ticker AND t.Fiscal_Year = :year
                """), {"value": new_value, "ticker": selected_ticker, "year": selected_year})
                if result_label == "M-Score":
                    connection.execute(text("""
                        UPDATE Fact_Risk_Analysis f
                        JOIN Dim_Company c ON c.Company_ID = f.Company_ID
                        JOIN Dim_Time t ON t.Time_ID = f.Time_ID
                        SET f.Status_178 = CASE WHEN f.M_Score > :baseline THEN 'Potential earnings manipulation' ELSE 'No potential earnings manipulation' END,
                            f.Status_222 = CASE WHEN f.M_Score > :sensitivity THEN 'Potential earnings manipulation' ELSE 'No potential earnings manipulation' END
                        WHERE c.Ticker_Code = :ticker AND t.Fiscal_Year = :year
                    """), {"baseline": BASELINE_THRESHOLD, "sensitivity": SENSITIVITY_THRESHOLD, "ticker": selected_ticker, "year": selected_year})
            st.success(f"{result_label} untuk {selected_ticker} tahun {selected_year} diperbarui.")
            st.rerun()
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
            st.error(f"Update gagal: {exc}")

    confirm = st.checkbox(f"Konfirmasi hapus hasil fact {selected_ticker} tahun {selected_year}", key="confirm_fact_delete")
    with st.container(key="data-management-delete"):
        if st.button("Delete Company - Year", disabled=not confirm, key="delete_fact"):
            try:
                _delete_fact_dialog(engine, selected_ticker, selected_year)
            except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
                st.error(f"Delete gagal. Hak DELETE database mungkin belum tersedia: {exc}")

    st.dataframe(rows, width="stretch", hide_index=True)
