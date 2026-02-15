import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="YTD", layout="wide")
st.title("YTD")

tables = require_tables()

ytd_raw, ytd_name = get_table(tables, "YTD plan v Actual")
if ytd_raw is None:
    st.error("Could not find YTD plan vs actual sheet. Check Data page load.")
    st.stop()

df_raw = ytd_raw.copy()
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
        if "division" in joined and "weeks" in joined:
            return i
        if "net" in joined and "plan" in joined:
            return i
        if "yards" in joined and "plan" in joined:
            return i
    return 2

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

header_row_idx = guess_header_row(df_raw)
df0 = promote_header_row(df_raw, header_row_idx)
df0.columns = make_unique_columns(df0.columns)

cols_clean = list(df0.columns)

time_col = find_first_col(cols_clean, ["week"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["weeks"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["period"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["month"])
if time_col is None:
    time_col = find_first_col(cols_clean, ["date"])

plan_col = find_first_col(cols_clean, ["plan", "yard"])
if plan_col is None:
    plan_col = find_first_col(cols_clean, ["yards", "plan"])
if plan_col is None:
    plan_col = find_first_col(cols_clean, ["planned"])

actual_col = find_first_col(cols_clean, ["net", "yards"])
if actual_col is None:
    actual_col = find_first_col(cols_clean, ["invoic"])
if actual_col is None:
    actual_col = find_first_col(cols_clean, ["actual"])
if actual_col is None:
    actual_col = find_first_col(cols_clean, ["produced", "yards"])

tab_dash, tab_head, tab_debug = st.tabs(["Dashboard", "Head", "Debug"])

with tab_dash:
    st.caption("Source sheet: " + str(ytd_name) + " | Header promoted from row: " + str(header_row_idx))

    if plan_col is None or actual_col is None:
        st.warning("Could not confidently detect Plan and Actual columns. See Debug tab.")
    else:
        if time_col is None:
            df_plot = df0[[plan_col, actual_col]].copy()
        else:
            df_plot = df0[[time_col, plan_col, actual_col]].copy()

        df_plot[plan_col] = _to_num(df_plot[plan_col])
        df_plot[actual_col] = _to_num(df_plot[actual_col])

        if time_col is not None and time_col in df_plot.columns:
            df_plot[time_col] = df_plot[time_col].astype(str).str.strip()
            bad_time_vals = {"", "", "none", "nat", "null"}
            df_plot = df_plot[~df_plot[time_col].str.lower().isin(bad_time_vals)].copy()

            time_as_num = pd.to_numeric(df_plot[time_col], errors="coerce")
            if time_as_num.notna().sum() > 0:
                df_plot = df_plot[time_as_num.notna()].copy()

            df_plot = df_plot.groupby(time_col, as_index=False)[[plan_col, actual_col]].sum()

            df_plot["_time_sort"] = pd.to_numeric(df_plot[time_col], errors="coerce")
            if df_plot["_time_sort"].notna().sum() > 0:
                df_plot = df_plot.sort_values("_time_sort")
            else:
                df_plot = df_plot.sort_values(time_col)

        total_plan = float(df_plot[plan_col].sum(skipna=True))
        total_actual = float(df_plot[actual_col].sum(skipna=True))
        total_var = total_actual - total_plan

        c1, c2, c3 = st.columns(3)
        c1.metric("Plan (sum)", fmt_int(total_plan))
        c2.metric("Actual or Net (sum)", fmt_int(total_actual))
        c3.metric("Variance (Actual - Plan)", fmt_int(total_var))

        if time_col is not None and time_col in df_plot.columns:
            st.subheader("Trend")
            st.line_chart(df_plot.set_index(time_col)[[plan_col, actual_col]], use_container_width=True)
        else:
            st.info("No time column detected for a trend chart. Totals only.")

with tab_head:
    st.subheader("Head (after header promotion + column dedupe)")
    st.dataframe(df0.head(60), use_container_width=True)

with tab_debug:
    st.subheader("Detected columns")
    st.write(
        {
            "source_sheet": ytd_name,
            "header_row_idx": header_row_idx,
            "time_col": time_col,
            "plan_col": plan_col,
            "actual_or_net_col": actual_col,
        }
    )

    if time_col is not None and time_col in df0.columns:
        st.subheader("Time bucket value counts (top 25)")
        st.write(df0[time_col].astype(str).str.strip().str.lower().value_counts().head(25))

    st.subheader("All columns (cleaned)")
    st.write(list(df0.columns))

    st.subheader("Raw head (before promotion)")
    st.dataframe(df_raw.head(10), use_container_width=True)
