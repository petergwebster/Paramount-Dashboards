import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="KPIs", layout="wide")
st.title("KPIs")

tables = st.session_state.get("sheets_raw")
if tables is None or not isinstance(tables, dict) or len(tables) == 0:
    st.warning("No data loaded. Go to Data and click Load and preview selected tabs.")
    st.stop()

st.caption("Using tables from st.session_state[sheets_raw]")

orders_raw = tables.get("Order Status for Angel Report")
if orders_raw is None:
    st.error("Missing sheet: Order Status for Angel Report")
    st.write("Available sheets")
    st.write(sorted(list(tables.keys())))
    st.stop()

orders_df = orders_raw.copy()
orders_df.columns = [str(c).strip() for c in orders_df.columns]

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

open_orders = len(orders_df)

yards_col = None
income_col = None

for c in orders_df.columns:
    if yards_col is None and "yards" in c.lower() and "written" in c.lower():
        yards_col = c
    if income_col is None and "income" in c.lower() and "written" in c.lower():
        income_col = c

open_yards_written = np.
open_income_written = np.

if yards_col is not None:
    open_yards_written = float(_to_num(orders_df[yards_col]).sum())

if income_col is not None:
    open_income_written = float(_to_num(orders_df[income_col]).sum())

c1, c2, c3 = st.columns(3)
c1.metric("Open Orders", _fmt_int(open_orders))
c2.metric("Open Yards Written", _fmt_int(open_yards_written))
c3.metric("Open Income Written", _fmt_money(open_income_written))

st.divider()

status_col = None
for c in orders_df.columns:
    if status_col is None and "status" in c.lower():
        status_col = c

if status_col is not None:
    st.subheader("Orders by " + status_col)
    status_counts = (
        orders_df[[status_col]]
        .dropna()
        .groupby(status_col, as_index=False)
        .size()
        .sort_values("size", ascending=False)
    )
    st.bar_chart(status_counts.set_index(status_col)["size"], use_container_width=True)
else:
    st.info("No status-like column found. Check the preview below.")

st.subheader("Preview: Order Status for Angel Report")
st.dataframe(orders_df.head(30), use_container_width=True)

with st.expander("Debug: columns"):
    st.write(list(orders_df.columns))
    st.write("Detected yards column")
    st.write(yards_col)
    st.write("Detected income column")
    st.write(income_col)
    st.write("Detected status column")
    st.write(status_col)
