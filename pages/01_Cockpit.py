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
        is_match = True
        for tok in required_tokens:
            if tok.lower() not in joined:
                is_match = False
                break
        if is_match:
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
    # Fast: reuse what your Data page already loaded.
    # We try a few common keys so this works without wiring.
    for key in ["sheets_raw", "sheets", "dfs", "dataframes", "sheet_previews"]:
        maybe = st.session_state.get(key)
        if isinstance(maybe, dict) and len(maybe) > 0:
            return maybe, key
    return None, None


def _safe_sum(df_in, col):
    if df_in is None or col not in df_in.columns:
        return np.
    return float(_to_num(df_in[col]).sum())


def _fmt_num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return "{:,.0f}".format(x)


def _fmt_money(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return "${:,.0f}".format(x)


def _fmt_pct(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return "{:.1f}%".format(100 * x)


def render():
    st.title("Cockpit")

    sheets_dict, source_key = _get_sheets_dict_from_session()
    if sheets_dict is None:
        st.warning("No loaded data found yet. Go to the Data page first to load dashboard.xlsx, then come back here.")
        return

    st.caption("Using data loaded in-memory from session_state key: " + str(source_key))

    # --- Get + clean required sheets (pivot-style header safe)
    ytd_raw = sheets_dict.get("YTD Plan vs Act")
    orders_raw = sheets_dict.get("Order Status for Angel Report")

    if ytd_raw is None or orders_raw is None:
        st.error("Missing required sheets in session data: `YTD Plan vs Act` and/or `Order Status for Angel Report`.")
        st.write("Available sheets")
        st.write(list(sheets_dict.keys()))
        return

    ytd_df = _clean_sheet_with_header(ytd_raw, ["Division", "Weeks", "Yards Produced", "Yards Planned"])
    orders_df = _clean_sheet_with_header(orders_raw, ["ORDER_NUMBER", "Yards Written", "Income Written"])

    # --- Coerce numeric columns
    for col in ["Weeks", "Yards Produced", "Yards Planned", "Income Produced", "Income Planned"]:
        if col in ytd_df.columns:
            ytd_df[col] = _to_num(ytd_df[col])

    for col in ["Yards Written", "Income Written", "Sum of QTY_INVOICED"]:
        if col in orders_df.columns:
            orders_df[col] = _to_num(orders_df[col])

    # --- Filter to valid YTD rows
    if "Division" in ytd_df.columns:
        ytd_valid = ytd_df[ytd_df["Division"].notna()].copy()
    else:
        ytd_valid = ytd_df.copy()

    # --- KPI calcs
    ytd_yards_produced = _safe_sum(ytd_valid, "Yards Produced")
    ytd_yards_planned = _safe_sum(ytd_valid, "Yards Planned")
    ytd_income_produced = _safe_sum(ytd_valid, "Income Produced")
    ytd_income_planned = _safe_sum(ytd_valid, "Income Planned")

    if ytd_yards_planned and not np.isnan(ytd_yards_planned):
        ytd_yards_vs_plan = ytd_yards_produced / ytd_yards_planned
    else:
        ytd_yards_vs_plan = np.

    if ytd_income_planned and not np.isnan(ytd_income_planned):
        ytd_income_vs_plan = ytd_income_produced / ytd_income_planned
    else:
        ytd_income_vs_plan = np.

    open_orders = int(orders_df["ORDER_NUMBER"].nunique()) if "ORDER_NUMBER" in orders_df.columns else np.
    open_yards_written = _safe_sum(orders_df, "Yards Written")
    open_income_written = _safe_sum(orders_df, "Income Written")

    # --- KPI tiles (dashes)
    st.subheader("YTD Plan vs Actual")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("YTD Yards Produced", _fmt_num(ytd_yards_produced))
    c2.metric("YTD Yards Planned", _fmt_num(ytd_yards_planned))
    c3.metric("Yards vs Plan", _fmt_pct(ytd_yards_vs_plan))
    c4.metric("YTD Income Produced", _fmt_money(ytd_income_produced))
    c5.metric("YTD Income Planned", _fmt_money(ytd_income_planned))
    c6.metric("Income vs Plan", _fmt_pct(ytd_income_vs_plan))

    st.subheader("Open Orders Summary")

    d1, d2, d3 = st.columns(3)
    if isinstance(open_orders, float) and np.isnan(open_orders):
        d1.metric("Open Orders", "NA")
    else:
        d1.metric("Open Orders", "{:,}".format(open_orders))

    d2.metric("Open Yards Written", _fmt_num(open_yards_written))
    d3.metric("Open Income Written", _fmt_money(open_income_written))

    st.divider()

    # --- Trend charts (weekly)
    if "Weeks" in ytd_valid.columns:
        yards_week = ytd_valid[[c for c in ["Weeks", "Yards Produced", "Yards Planned"] if c in ytd_valid.columns]].copy()
        yards_week = yards_week.dropna(subset=["Weeks"])
        yards_week = yards_week.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

        st.subheader("Yards Produced vs Planned by Week")
        if "Yards Produced" in yards_week.columns and "Yards Planned" in yards_week.columns and len(yards_week) > 0:
            st.line_chart(yards_week.set_index("Weeks")[["Yards Produced", "Yards Planned"]], use_container_width=True)
        else:
            st.info("Weekly yards chart not available after cleaning.")

        income_week = ytd_valid[[c for c in ["Weeks", "Income Produced", "Income Planned"] if c in ytd_valid.columns]].copy()
        income_week = income_week.dropna(subset=["Weeks"])
        income_week = income_week.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

        st.subheader("Income Produced vs Planned by Week")
        if "Income Produced" in income_week.columns and "Income Planned" in income_week.columns and len(income_week) > 0:
            st.line_chart(income_week.set_index("Weeks")[["Income Produced", "Income Planned"]], use_container_width=True)
        else:
            st.info("Weekly income chart not available after cleaning.")
    else:
        st.info("No `Weeks` column found in the cleaned YTD sheet, so weekly trend charts are hidden.")

    with st.expander("Debug (cleaned tables)"):
        st.write("YTD Plan vs Act cleaned (first 25 rows)")
        st.dataframe(ytd_valid.head(25), use_container_width=True)
        st.write("Order Status cleaned (first 25 rows)")
        st.dataframe(orders_df.head(25), use_container_width=True)


render()
