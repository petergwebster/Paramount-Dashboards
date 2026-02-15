import streamlit as st
import pandas as pd

st.set_page_config(page_title="KPIs", layout="wide")
st.title("KPIs")

tables = st.session_state.get("sheets_raw")
if tables is None or not isinstance(tables, dict) or len(tables) == 0:
    st.warning("No data loaded. Go to Data and click Load and preview selected tabs.")
    st.stop()

sheet_name = "Order Status for Angel Report"
orders_raw = tables.get(sheet_name)

if orders_raw is None:
    st.error("Missing sheet: " + sheet_name)
    st.write("Available sheets")
    st.write(sorted(list(tables.keys())))
    st.stop()

def _promote_header_row(df_in, must_contain_tokens, scan_rows=80):
    # Finds the row that contains required tokens, then uses it as the header
    scan_rows = min(scan_rows, len(df_in))
    for ridx in range(scan_rows):
        row_vals = [str(x).strip() for x in df_in.iloc[ridx].tolist()]
        joined = " | ".join(row_vals).upper()
        ok = True
        for tok in must_contain_tokens:
            if tok.upper() not in joined:
                ok = False
                break
        if ok:
            new_cols = []
            for v in row_vals:
                v2 = str(v).strip()
                if v2 == "" or v2.lower() == "none" or v2.lower() == "":
                    v2 = "col_" + str(len(new_cols) + 1)
                new_cols.append(v2)

            df_out = df_in.iloc[ridx + 1:].copy().reset_index(drop=True)
            df_out.columns = new_cols
            df_out.columns = [str(c).strip() for c in df_out.columns]
            return df_out, ridx
    return df_in.copy(), None

orders_df0 = orders_raw.copy()
orders_df0.columns = [str(c).strip() for c in orders_df0.columns]

orders_df, hdr_row = _promote_header_row(
    orders_df0,
    must_contain_tokens=["ORDER_NUMBER", "LINE_NUMBER"],
    scan_rows=120
)

st.caption("Header row detected at: " + (str(hdr_row) if hdr_row is not None else "NA"))

st.subheader("Top KPIs")

open_orders = int(len(orders_df))

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

def _fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _fmt_money(x):
    if x is None:
        return "NA"
    try:
        return "${:,.0f}".format(float(x))
    except Exception:
        return "NA"

yards_col = None
income_col = None
status_col = None

for c in orders_df.columns:
    c_low = str(c).lower()
    if yards_col is None and "yard" in c_low and "written" in c_low:
        yards_col = c
    if income_col is None and "income" in c_low and "written" in c_low:
        income_col = c
    if status_col is None and "status" in c_low:
        status_col = c

open_yards_written = None
open_income_written = None

if yards_col is not None:
    open_yards_written = float(_to_num(orders_df[yards_col]).sum())

if income_col is not None:
    open_income_written = float(_to_num(orders_df[income_col]).sum())

c1, c2, c3 = st.columns(3)
c1.metric("Open Orders", _fmt_int(open_orders))
c2.metric("Open Yards Written", _fmt_int(open_yards_written))
c3.metric("Open Income Written", _fmt_money(open_income_written))

st.divider()

st.subheader("Orders by status")
if status_col is None:
    st.info("No status-like column found after header fix. See Debug below.")
else:
    status_counts = (
        orders_df[[status_col]]
        .dropna()
        .groupby(status_col, as_index=False)
        .size()
        .sort_values("size", ascending=False)
    )
    st.bar_chart(status_counts.set_index(status_col)["size"], use_container_width=True)

st.subheader("Preview")
st.dataframe(orders_df.head(30), use_container_width=True)

with st.expander("Debug"):
    st.write("Detected yards column")
    st.write(yards_col)
    st.write("Detected income column")
    st.write(income_col)
    st.write("Detected status column")
    st.write(status_col)
    st.write("All columns")
    st.write(list(orders_df.columns))
