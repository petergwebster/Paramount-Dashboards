import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Weekly", layout="wide")
st.title("Weekly")

tables = require_tables()

weekly_df, weekly_name = get_table(tables, "Written produced by week")
if weekly_df is None:
    weekly_df, weekly_name = get_table(tables, "Written produced invoiced")

if weekly_df is None:
    st.error("Could not find weekly sheet (Written Produced...). Check Data page load.")
    st.stop()

df0 = weekly_df.copy()
df0.columns = [str(c).strip() for c in df0.columns]

def _find_time_col(cols):
    prefs = ["week", "wk", "period", "date", "month", "fiscal"]
    for p in prefs:
        for c in cols:
            if p in str(c).lower():
                return c
    return None

def _find_measure_col(cols, keywords):
    for c in cols:
        c_low = str(c).lower()
        ok = True
        for kw in keywords:
            if kw not in c_low:
                ok = False
                break
        if ok:
            return c
    return None

time_col = _find_time_col(df0.columns)

written_col = _find_measure_col(df0.columns, ["written"])
produced_col = _find_measure_col(df0.columns, ["produced"])
invoiced_col = _find_measure_col(df0.columns, ["invoic"])

if written_col is None:
    written_col = _find_measure_col(df0.columns, ["write"])
if invoiced_col is None:
    invoiced_col = _find_measure_col(df0.columns, ["invoice"])

def _to_num(s):
    return pd.to_numeric(s, errors="coerce")

def _fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _safe_last_val(series_in):
    s2 = _to_num(series_in)
    s2 = s2.dropna()
    if len(s2) == 0:
        return None
    return float(s2.iloc[-1])

def _safe_prev_val(series_in):
    s2 = _to_num(series_in)
    s2 = s2.dropna()
    if len(s2) < 2:
        return None
    return float(s2.iloc[-2])

df_chart = df0.copy()

if time_col is not None:
    df_chart[time_col] = df_chart[time_col].astype(str).str.strip()

for c in [written_col, produced_col, invoiced_col]:
    if c is not None and c in df_chart.columns:
        df_chart[c] = _to_num(df_chart[c])

if time_col is not None:
    df_chart = df_chart.dropna(subset=[time_col])

st.caption("Source sheet: " + str(weekly_name))

st.subheader("Latest period KPIs")

k1, k2, k3 = st.columns(3)

latest_written = _safe_last_val(df_chart[written_col]) if written_col is not None else None
prev_written = _safe_prev_val(df_chart[written_col]) if written_col is not None else None

latest_produced = _safe_last_val(df_chart[produced_col]) if produced_col is not None else None
prev_produced = _safe_prev_val(df_chart[produced_col]) if produced_col is not None else None

latest_invoiced = _safe_last_val(df_chart[invoiced_col]) if invoiced_col is not None else None
prev_invoiced = _safe_prev_val(df_chart[invoiced_col]) if invoiced_col is not None else None

k1.metric("Written (latest)", _fmt_int(latest_written), None if prev_written is None else _fmt_int(latest_written - prev_written))
k2.metric("Produced (latest)", _fmt_int(latest_produced), None if prev_produced is None else _fmt_int(latest_produced - prev_produced))
k3.metric("Invoiced (latest)", _fmt_int(latest_invoiced), None if prev_invoiced is None else _fmt_int(latest_invoiced - prev_invoiced))

st.divider()

st.subheader("Trend")
measure_cols = []
if written_col is not None:
    measure_cols.append(written_col)
if produced_col is not None:
    measure_cols.append(produced_col)
if invoiced_col is not None:
    measure_cols.append(invoiced_col)

if time_col is None:
    st.info("No obvious time column found. Showing first 120 rows only.")
    st.dataframe(df_chart.head(120), use_container_width=True)
else:
    plot_df = df_chart[[time_col] + measure_cols].copy()
    plot_df = plot_df.dropna(subset=[time_col])
    plot_df = plot_df.tail(150)

    plot_df = plot_df.set_index(time_col)
    st.line_chart(plot_df, use_container_width=True)

st.divider()

with st.expander("Debug"):
    st.write("Detected time column")
    st.write(time_col)
    st.write("Detected measure columns")
    st.write({"written": written_col, "produced": produced_col, "invoiced": invoiced_col})
    st.write("All columns")
    st.write(list(df0.columns))
    st.write("Head")
    st.dataframe(df0.head(20), use_container_width=True)
