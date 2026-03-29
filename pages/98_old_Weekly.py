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
    out_cols = []
    for c in cols:
        base = "" if c is None else str(c)
        base = base.strip()
        if base == "" or base.lower() in ["", "none", "nat", "null"]:
            base = "unnamed"
        if base not in seen:
            seen[base] = 0
            out_cols.append(base)
        else:
            seen[base] += 1
            out_cols.append(base + "__" + str(seen[base]))
    return out_cols

def promote_header_row(df_in, header_row_idx):
    df2 = df_in.copy()
    new_cols = df2.iloc[header_row_idx].astype(str).tolist()
    df2.columns = [str(c).strip() for c in new_cols]
    df2 = df2.iloc[header_row_idx + 1 :].reset_index(drop=True)
    return df2

def guess_header_row(df_in, max_scan_rows=25):
    scan_rows = min(max_scan_rows, len(df_in))
    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)
        if "division" in joined and "week" in joined:
            return i
        if "weeks" in joined and "yards" in joined:
            return i
        if "yards" in joined and "written" in joined and "produced" in joined:
            return i
        if "yards wr" in joined and "yards prod" in joined:
            return i
    return 4

def find_first_col(cols, keywords):
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

def fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def safe_last(series_in):
    s2 = _to_num(series_in).dropna()
    if len(s2) == 0:
        return None
    return float(s2.iloc[-1])

def safe_prev(series_in):
    s2 = _to_num(series_in).dropna()
    if len(s2) < 2:
        return None
    return float(s2.iloc[-2])

def metric_delta(curr_val, prev_val):
    if curr_val is None or prev_val is None:
        return None
    try:
        return float(curr_val) - float(prev_val)
    except Exception:
        return None

header_row_idx = guess_header_row(df_raw)
df0 = promote_header_row(df_raw, header_row_idx)
df0.columns = make_unique_columns(df0.columns)

cols_clean = list(df0.columns)

time_col = find_first_col(cols_clean, ["week"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["weeks"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["wk"])

written_col = find_first_col(cols_clean, ["written"])
if written_col is None:
    written_col = find_first_col(cols_clean, ["yards", "wr"])

produced_col = find_first_col(cols_clean, ["produced"])
if produced_col is None:
    produced_col = find_first_col(cols_clean, ["yards", "prod"])

invoiced_col = find_first_col(cols_clean, ["invoiced"])
if invoiced_col is None:
    invoiced_col = find_first_col(cols_clean, ["net"])
if invoiced_col is None:
    invoiced_col = find_first_col(cols_clean, ["income"])

tab_dash, tab_head, tab_debug = st.tabs(["Dashboard", "Head", "Debug"])

with tab_dash:
    st.subheader("Weekly snapshot")

    st.caption("Source sheet: " + str(weekly_name) + " | Header promoted from row: " + str(header_row_idx))

    if time_col is None:
        st.warning("Could not detect a Week column. See Debug tab.")
    else:
        use_cols = []
        if written_col is not None:
            use_cols.append(written_col)
        if produced_col is not None:
            use_cols.append(produced_col)
        if invoiced_col is not None:
            use_cols.append(invoiced_col)

        if len(use_cols) == 0:
            st.warning("Could not detect Written/Produced/Invoiced columns. See Debug tab.")
        else:
            df_plot = df0[[time_col] + use_cols].copy()

            df_plot[time_col] = df_plot[time_col].astype(str).str.strip()
            bad_time_vals = {"", "", "none", "nat", "null"}
            df_plot = df_plot[~df_plot[time_col].str.lower().isin(bad_time_vals)].copy()

            time_as_num = pd.to_numeric(df_plot[time_col], errors="coerce")
            if time_as_num.notna().sum() > 0:
                df_plot = df_plot[time_as_num.notna()].copy()

            for c in use_cols:
                df_plot[c] = _to_num(df_plot[c])

            df_plot = df_plot.groupby(time_col, as_index=False)[use_cols].sum()

            df_plot["_time_sort"] = pd.to_numeric(df_plot[time_col], errors="coerce")
            if df_plot["_time_sort"].notna().sum() > 0:
                df_plot = df_plot.sort_values("_time_sort")
            else:
                df_plot = df_plot.sort_values(time_col)

            last_written = safe_last(df_plot[written_col]) if written_col is not None else None
            prev_written = safe_prev(df_plot[written_col]) if written_col is not None else None

            last_produced = safe_last(df_plot[produced_col]) if produced_col is not None else None
            prev_produced = safe_prev(df_plot[produced_col]) if produced_col is not None else None

            last_invoiced = safe_last(df_plot[invoiced_col]) if invoiced_col is not None else None
            prev_invoiced = safe_prev(df_plot[invoiced_col]) if invoiced_col is not None else None

            c1, c2, c3 = st.columns(3)

            if written_col is not None:
                c1.metric(
                    "Written (latest)",
                    fmt_int(last_written),
                    fmt_int(metric_delta(last_written, prev_written)),
                )
            if produced_col is not None:
                c2.metric(
                    "Produced (latest)",
                    fmt_int(last_produced),
                    fmt_int(metric_delta(last_produced, prev_produced)),
                )
            if invoiced_col is not None:
                c3.metric(
                    "Invoiced or Net (latest)",
                    fmt_int(last_invoiced),
                    fmt_int(metric_delta(last_invoiced, prev_invoiced)),
                )

            st.subheader("Trend")
            st.line_chart(df_plot.set_index(time_col)[use_cols], use_container_width=True)

with tab_head:
    st.subheader("Head (after header promotion and dedupe)")
    st.dataframe(df0.head(60), use_container_width=True)

with tab_debug:
    st.subheader("Detected columns")
    st.write(
        {
            "source_sheet": weekly_name,
            "header_row_idx": header_row_idx,
            "time_col": time_col,
            "written_col": written_col,
            "produced_col": produced_col,
            "invoiced_or_net_col": invoiced_col,
        }
    )

    if time_col is not None and time_col in df0.columns:
        st.subheader("Time bucket value counts (top 25)")
        st.write(
            df0[time_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .value_counts()
            .head(25)
        )

    st.subheader("All columns (cleaned)")
    st.write(list(df0.columns))

    st.subheader("Raw head (before promotion)")
    st.dataframe(df_raw.head(10), use_container_width=True)
