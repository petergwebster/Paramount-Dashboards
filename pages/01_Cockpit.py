import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

def _fmt_int(x):
    if x is None:
        return "NA"
    if isinstance(x, float) and np.isnan(x):
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _fmt_money(x):
    if x is None:
        return "NA"
    if isinstance(x, float) and np.isnan(x):
        return "NA"
    try:
        return "${:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _safe_sum(df_in, col_name):
    if df_in is None:
        return np.
    if col_name not in df_in.columns:
        return np.
    return float(_to_num(df_in[col_name]).sum())

def _safe_count(df_in, col_name=None):
    if df_in is None:
        return np.
    if col_name is None:
        return int(len(df_in))
    if col_name not in df_in.columns:
        return np.
    return int(df_in[col_name].notna().sum())

def _get_tables_from_session():
    if "sheets_raw" in st.session_state and isinstance(st.session_state["sheets_raw"], dict):
        if len(st.session_state["sheets_raw"]) > 0:
            return st.session_state["sheets_raw"]
    return None

tables = _get_tables_from_session()
if tables is None:
    st.warning("No data loaded yet. Go to the Data page and click Load and preview selected tabs.")
    st.stop()

tab_kpis, tab_orders, tab_debug = st.tabs(["KPIs", "Orders", "Debug"])

with tab_kpis:
    st.subheader("Top KPIs (from Order Status for Angel Report)")

    orders_raw = tables.get("Order Status for Angel Report")
    if orders_raw is None:
        st.error("Missing sheet: Order Status for Angel Report")
    else:
        orders_df = orders_raw.copy()

        # Normalize column names a bit (strip spaces)
        orders_df.columns = [str(c).strip() for c in orders_df.columns]

        # KPIs based on common columns we’ve seen in this workbook style
        open_orders = _safe_count(orders_df, "ORDER_NUMBER") if "ORDER_NUMBER" in orders_df.columns else _safe_count(orders_df)
        open_yards_written = _safe_sum(orders_df, "Yards Written")
        open_income_written = _safe_sum(orders_df, "Income Written")

        c1, c2, c3 = st.columns(3)
        c1.metric("Open Orders", _fmt_int(open_orders))
        c2.metric("Open Yards Written", _fmt_int(open_yards_written))
        c3.metric("Open Income Written", _fmt_money(open_income_written))

        st.caption("If Yards Written or Income Written show NA, it just means the column name in your sheet is slightly different. Check the Debug tab for the exact column names.")

with tab_orders:
    st.subheader("Orders by Status")

    orders_raw = tables.get("Order Status for Angel Report")
    if orders_raw is None:
        st.error("Missing sheet: Order Status for Angel Report")
    else:
        orders_df = orders_raw.copy()
        orders_df.columns = [str(c).strip() for c in orders_df.columns]

        if "Yard Order Status" in orders_df.columns:
            status_counts = (
                orders_df[["Yard Order Status"]]
                .dropna()
                .groupby("Yard Order Status", as_index=False)
                .size()
                .sort_values("size", ascending=False)
            )

            st.dataframe(status_counts, use_container_width=True)
            st.bar_chart(status_counts.set_index("Yard Order Status")["size"], use_container_width=True)
        else:
            st.info("Column not found: Yard Order Status")
            st.write("Available columns")
            st.write(list(orders_df.columns))

        st.subheader("Raw preview")
        st.dataframe(orders_df.head(25), use_container_width=True)

with tab_debug:
    st.subheader("Debug")

    st.write("Session state keys")
    st.write(sorted(list(st.session_state.keys())))

    st.write("Sheets loaded")
    st.write(sorted(list(tables.keys())))

    orders_raw = tables.get("Order Status for Angel Report")
    if orders_raw is not None:
        st.write("Order Status for Angel Report shape")
        st.write(orders_raw.shape)

        st.write("Order Status for Angel Report columns")
        st.write([str(c) for c in orders_raw.columns])

        st.write("Order Status for Angel Report preview")
        st.dataframe(orders_raw.head(30), use_container_width=True)
