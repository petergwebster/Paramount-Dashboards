import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Cockpit", layout="wide")

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

def _find_header_row(df_in, required_tokens, max_scan=60):
    max_scan = min(max_scan, len(df_in))
    for ridx in range(max_scan):
        row_vals = [str(x).strip() for x in df_in.iloc[ridx].tolist()]
        joined = " | ".join(row_vals).lower()
        ok = True
        for tok in required_tokens:
            if tok.lower() not in joined:
                ok = False
                break
        if ok:
            return ridx
    return None

def _clean_sheet_with_header(df_in, required_tokens):
    hdr_idx = _find_header_row(df_in, required_tokens)
    if hdr_idx is None:
        df_out = df_in.copy().reset_index(drop=True)
        df_out.columns = [str(c).strip() for c in df_out.columns]
        return df_out

    new_cols = [str(x).strip() for x in df_in.iloc[hdr_idx].tolist()]
    df_out = df_in.iloc[hdr_idx + 1:].copy()
    df_out.columns = new_cols
    df_out = df_out.reset_index(drop=True)
    df_out.columns = [c.strip() for c in df_out.columns]
    return df_out

def _get_sheets_dict_from_session():
    # Assumption to move ahead: your Data tab stored sheets into one of these common keys.
    # We try a few so you don’t have to wire anything up right now.
    for key in ["sheets_raw", "sheets", "dfs", "dataframes", "sheet_previews"]:
        maybe = st.session_state.get(key)
        if isinstance(maybe, dict) and len(maybe) > 0:
            return maybe, key
    return None, None

def _safe_sum(df_in, col):
    if df_in is None or col not in df_in.columns:
        return np.
    return float(pd.to_numeric(df_in[col], errors="coerce").sum())

def render():
    st.title("Cockpit")

    sheets_dict, source_key = _get_sheets_dict_from_session()
    if sheets_dict is None:
        st.warning("No loaded data found in session. Go to your Data tab first (the one that loads dashboard.xlsx).")
        return

    st.caption("Using data from st.session_state[" + source_key + "]")

    # --- Load required sheets from session
    ytd_raw = sheets_dict.get("YTD Plan vs Act")
    orders_raw = sheets_dict.get("Order Status for Angel Report")

    if ytd_raw is None or orders_raw is None:
        st.error("Missing required sheets in session. Need `YTD Plan vs Act` and `Order Status for Angel Report`.")
        st.write("Available sheets")
        st.write(list(sheets_dict.keys()))
        return

    # --- Clean (handles pivot-style pre-header rows)
    ytd_df = _clean_sheet_with_header(ytd_raw, ["Division", "Weeks", "Yards Produced", "Yards Planned"])
    orders_df = _clean_sheet_with_header(orders_raw, ["ORDER_NUMBER", "Yards Written", "Income Written"])

    # --- Coerce numerics for YTD
    for col in ["Weeks", "Yards Produced", "Yards Planned", "Income Produced", "Income Planned"]:
        if col in ytd_df.columns:
            ytd_df[col] = _to_num(ytd_df[col])

    # Keep only rows that look like actual division rows
    if "Division" in ytd_df.columns:
        ytd_valid = ytd_df[ytd_df["Division"].notna()].copy()
    else:
        ytd_valid = ytd_df.copy()

    # --- Coerce numerics for Orders
    for col in ["Yards Written", "Income Written"]:
        if col in orders_df.columns:
            orders_df[col] = _to_num(orders_df[col])

    # --- KPI Totals
    ytd_yards_produced = _safe_sum(ytd_valid, "Yards Produced")
    ytd_yards_planned = _safe_sum(ytd_valid, "Yards Planned")
    ytd_income_produced = _safe_sum(ytd_valid, "Income Produced")
    ytd_income_planned = _safe_sum(ytd_valid, "Income Planned")

    ytd_yards_vs_plan = (ytd_yards_produced / ytd_yards_planned) if ytd_yards_planned and not np.isnan(ytd_yards_planned) else np.
    ytd_income_vs_plan = (ytd_income_produced / ytd_income_planned) if ytd_income_planned and not np.isnan(ytd_income_planned) else np.

    open_orders = int(orders_df["ORDER_NUMBER"].nunique()) if "ORDER_NUMBER" in orders_df.columns else np.
    open_yards_written = _safe_sum(orders_df, "Yards Written")
    open_income_written = _safe_sum(orders_df, "Income Written")

    # --- Display KPI Tiles
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("YTD Yards Produced", "{:,.0f}".format(ytd_yards_produced) if not np.isnan(ytd_yards_produced) else "NA")
    c2.metric("YTD Yards Planned", "{:,.0f}".format(ytd_yards_planned) if not np.isnan(ytd_yards_planned) else "NA")
    c3.metric("Yards vs Plan", "{:.1f}%".format(100 * ytd_yards_vs_plan) if not np.isnan(ytd_yards_vs_plan) else "NA")

    c4.metric("YTD Income Produced", "${:,.0f}".format(ytd_income_produced) if not np.isnan(ytd_income_produced) else "NA")
    c5.metric("YTD Income Planned", "${:,.0f}".format(ytd_income_planned) if not np.isnan(ytd_income_planned) else "NA")
    c6.metric("Income vs Plan", "{:.1f}%".format(100 * ytd_income_vs_plan) if not np.isnan(ytd_income_vs_plan) else "NA")

    d1, d2, d3 = st.columns(3)
    d1.metric("Open Orders", "{:,}".format(open_orders) if not isinstance(open_orders, float) else "NA")
    d2.metric("Open Yards Written", "{:,.0f}".format(open_yards_written) if not np.isnan(open_yards_written) else "NA")
    d3.metric("Open Income Written", "${:,.0f}".format(open_income_written) if not np.isnan(open_income_written) else "NA")

    st.divider()

    # --- Trend charts (weekly)
    if "Weeks" in ytd_valid.columns:
        ytd_week_yards = ytd_valid[[c for c in ["Weeks", "Yards Produced", "Yards Planned"] if c in ytd_valid.columns]].copy()
        ytd_week_yards = ytd_week_yards.dropna(subset=["Weeks"])
        ytd_week_yards = ytd_week_yards.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

        st.subheader("Produced vs Planned (Yards) by Week")
        if "Yards Produced" in ytd_week_yards.columns and "Yards Planned" in ytd_week_yards.columns:
            st.line_chart(ytd_week_yards.set_index("Weeks")[["Yards Produced", "Yards Planned"]])
        else:
            st.info("Missing columns for yards trend chart.")

        ytd_week_income = ytd_valid[[c for c in ["Weeks", "Income Produced", "Income Planned"] if c in ytd_valid.columns]].copy()
        ytd_week_income = ytd_week_income.dropna(subset=["Weeks"])
        ytd_week_income = ytd_week_income.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

        st.subheader("Produced vs Planned (Income) by Week")
        if "Income Produced" in ytd_week_income.columns and "Income Planned" in ytd_week_income.columns:
            st.line_chart(ytd_week_income.set_index("Weeks")[["Income Produced", "Income Planned"]])
        else:
            st.info("Missing columns for income trend chart.")
    else:
        st.info("No `Weeks` column found in YTD sheet after cleaning, so weekly trend charts are hidden.")

    with st.expander("Debug: show cleaned inputs"):
        st.write("YTD Plan vs Act cleaned (head)")
        st.dataframe(ytd_valid.head(30), use_container_width=True)
        st.write("Order Status cleaned (head)")
        st.dataframe(orders_df.head(30), use_container_width=True)

render()
