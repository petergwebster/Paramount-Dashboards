import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Weekly", layout="wide")
st.title("Weekly")

tables = require_tables()

weekly_raw, weekly_name = get_table(tables, "Written produced by week")
if weekly_raw is None:
    weekly_raw, weekly_name = get_table(tables, "Written produced invoiced")

if weekly_raw is None:
    st.error("Could not find weekly sheet. Check Data page load.")
    st.stop()

df_raw = weekly_raw.copy()
df_raw.columns = [str(c).strip() for c in df_raw.columns]

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

def make_unique_columns(cols):
    seen = {}
    new_cols = []
    for c in cols:
        base = "" if c is None else str(c)
        base = base.strip()
        if base == "" or base.lower() == "" or base.lower() == "none":
            base = "unnamed"

        if base not in seen:
            seen[base] = 0
            new_cols.append(base)
        else:
            seen[base] += 1
            new_cols.append(base + "__" + str(seen[base]))
    return new_cols

def promote_header_row(df_in, header_row_idx):
    df2 = df_in.copy()
    new_cols = df2.iloc[header_row_idx].astype(str).tolist()
    df2.columns = [str(c).strip() for c in new_cols]
    df2 = df2.iloc[header_row_idx + 1 :].reset_index(drop=True)
    return df2

def guess_header_row(df_in, max_scan_rows=20):
    scan_rows = min(max_scan_rows, len(df_in))
    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)
        if "division" in joined and "week" in joined:
            return i
        if "divisions" in joined and "weeks" in joined:
            return i
        if "weeks" in joined and "yards" in joined:
            return i
    return 4

def _find_time_col(cols):
    prefs = ["week", "weeks", "wk", "period", "date", "month", "fiscal"]
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

def _fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _safe_last(series_in):
    s2 = _to_num(series_in).dropna()
    if len(s2) == 0:
        return None
    return float(s2.iloc[-1])

def _safe_prev(series_in):
    s2 = _to_num(series_in).dropna()
    if len(s2) < 2:
        return None
    return float(s2.iloc[-2])

def _metric_delta(last_val, prev_val):
    if last_val is None or prev_val is None:
        return None
    return float(last_val) - float(prev_val)

header_row_idx = guess_header_row(df_raw, max_scan_rows=20)
df0 = promote_header_row(df_raw, header_row_idx)

df0.columns = make_unique_columns(df0.columns)
df0 = df0.loc[:, [c for c in df0.columns if str(c).strip() != ""]]

time_col = _find_time_col(df0.columns)

written_col = _find_measure_col(df0.columns, ["written"])
produced_col = _find_measure_col(df0.columns, ["produced"])
invoiced_col = _find_measure_col(df0.columns, ["invoic"])

if written_col is None:
    written_col = _find_measure_col(df0.columns, ["write"])
if invoiced_col is None:
    invoiced_col = _find_measure_col(df0.columns, ["invoice"])
if invoiced_col is None:
    invoiced_col = _find_measure_col(df0.columns, ["net"])

st.caption("Source sheet: " + str(weekly_name) + " | Header promoted from row: " + str(header_row_idx))

tab_dash, tab_head, tab_debug = st.tabs(["Dashboard", "Head", "Debug"])

with tab_dash:
    if time_col is None:
        st.error("Could not detect a week/date column. Check Debug tab.")
    else:
        df_chart = df0.copy()
        df_chart[time_col] = df_chart[time_col].astype(str).str.strip()

        measure_cols = []
        for c in [written_col, produced_col, invoiced_col]:
            if c is not None and c in df_chart.columns:
                measure_cols.append(c)

        if len(measure_cols) == 0:
            st.error("Could not detect written/produced/invoiced numeric columns. Check Debug tab.")
        else:
            df_plot = df_chart[[time_col] + measure_cols].copy()
            for c in measure_cols:
                df_plot[c] = _to_num(df_plot[c])

            df_plot = df_plot.dropna(subset=[time_col])
            df_plot = df_plot.groupby(time_col, as_index=False)[measure_cols].sum()

            df_plot["_time_sort"] = pd.to_numeric(df_plot[time_col], errors="coerce")
            if df_plot["_time_sort"].notna().sum() > 0:
                df_plot = df_plot.sort_values("_time_sort")
            else:
                df_plot = df_plot.sort_values(time_col)

            last_written = _safe_last(df_plot[written_col]) if written_col is not None else None
            prev_written = _safe_prev(df_plot[written_col]) if written_col is not None else None

            last_produced = _safe_last(df_plot[produced_col]) if produced_col is not None else None
            prev_produced = _safe_prev(df_plot[produced_col]) if produced_col is not None else None

            last_invoiced = _safe_last(df_plot[invoiced_col]) if invoiced_col is not None else None
            prev_invoiced = _safe_prev(df_plot[invoiced_col]) if invoiced_col is not None else None

            c1, c2, c3 = st.columns(3)

            if written_col is not None:
                c1.metric(
                    "Written (latest)",
                    _fmt_int(last_written),
                    _fmt_int(_metric_delta(last_written, prev_written)),
                )
            if produced_col is not None:
                c2.metric(
                    "Produced (latest)",
                    _fmt_int(last_produced),
                    _fmt_int(_metric_delta(last_produced, prev_produced)),
                )
            if invoiced_col is not None:
                c3.metric(
                    "Invoiced or Net (latest)",
                    _fmt_int(last_invoiced),
                    _fmt_int(_metric_delta(last_invoiced, prev_invoiced)),
                )

            st.subheader("Trend")
            st.line_chart(df_plot.set_index(time_col)[measure_cols], use_container_width=True)

with tab_head:
    st.subheader("Head (after header promotion and dedupe)")
    st.dataframe(df0.head(60), use_container_width=True)

with tab_debug:
    st.subheader("Detected columns")
    st.write(
        {
            "time_col": time_col,
            "written_col": written_col,
            "produced_col": produced_col,
            "invoiced_or_net_col": invoiced_col,
        }
    )

    st.subheader("All columns (cleaned)")
    st.write(list(df0.columns))

    st.subheader("Raw head (before promotion)")
    st.dataframe(df_raw.head(10), use_container_width=True)
