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
    if df_in is None:
        return None

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

st.title("Cockpit")

tables = st.session_state.get("sheets_raw")
if not isinstance(tables, dict) or len(tables) == 0:
    st.warning("No data loaded yet. Go to the Data page and click Load and preview selected tabs, then come back.")
    st.stop()

st.caption("Using sheets from st.session_state[sheets_raw]. Loaded sheets: " + str(len(tables)))

tab_summary, tab_orders, tab_debug = st.tabs(["Summary", "Orders", "Debug"])

with tab_summary:
    st.subheader("YTD Plan vs Actual")

    ytd_raw = tables.get("YTD Plan vs Act")
    if ytd_raw is None:
        st.error("Missing sheet: YTD Plan vs Act")
    else:
        ytd_df = _clean_sheet_with_header(ytd_raw, required_tokens=["Weeks", "Yards Produced"])
        if ytd_df is None:
            st.error("Could not clean YTD sheet")
        else:
            ytd_yards_produced = _safe_sum(ytd_df, "Yards Produced")
            ytd_yards_planned = _safe_sum(ytd_df, "Yards Planned")
            ytd_income_produced = _safe_sum(ytd_df, "Income Produced")
            ytd_income_planned = _safe_sum(ytd_df, "Income Planned")

            ytd_yards_vs_plan = np.
            if not (isinstance(ytd_yards_planned, float) and np.isnan(ytd_yards_planned)) and ytd_yards_planned != 0:
                ytd_yards_vs_plan = (ytd_yards_produced - ytd_yards_planned) / ytd_yards_planned

            ytd_income_vs_plan = np.
            if not (isinstance(ytd_income_planned, float) and np.isnan(ytd_income_planned)) and ytd_income_planned != 0:
                ytd_income_vs_plan = (ytd_income_produced - ytd_income_planned) / ytd_income_planned

            c1, c2, c3 = st.columns(3)
            c1.metric("YTD Yards Produced", _fmt_num(ytd_yards_produced))
            c2.metric("YTD Yards Planned", _fmt_num(ytd_yards_planned))
            c3.metric("Yards vs Plan", _fmt_pct(ytd_yards_vs_plan))

            c4, c5, c6 = st.columns(3)
            c4.metric("YTD Income Produced", _fmt_money(ytd_income_produced))
            c5.metric("YTD Income Planned", _fmt_money(ytd_income_planned))
            c6.metric("Income vs Plan", _fmt_pct(ytd_income_vs_plan))

            st.divider()

            if "Weeks" in ytd_df.columns:
                yards_week_cols = [c for c in ["Weeks", "Yards Produced", "Yards Planned"] if c in ytd_df.columns]
                income_week_cols = [c for c in ["Weeks", "Income Produced", "Income Planned"] if c in ytd_df.columns]

                yards_week = ytd_df[yards_week_cols].copy()
                yards_week["Weeks"] = _to_num(yards_week["Weeks"])
                yards_week = yards_week.dropna(subset=["Weeks"])
                yards_week = yards_week.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

                st.subheader("Yards Produced vs Planned by Week")
                if "Yards Produced" in yards_week.columns and "Yards Planned" in yards_week.columns and len(yards_week) > 0:
                    st.line_chart(yards_week.set_index("Weeks")[["Yards Produced", "Yards Planned"]], use_container_width=True)
                else:
                    st.info("Not enough columns to chart weekly yards.")

                income_week = ytd_df[income_week_cols].copy()
                income_week["Weeks"] = _to_num(income_week["Weeks"])
                income_week = income_week.dropna(subset=["Weeks"])
                income_week = income_week.groupby("Weeks", as_index=False).sum().sort_values("Weeks")

                st.subheader("Income Produced vs Planned by Week")
                if "Income Produced" in income_week.columns and "Income Planned" in income_week.columns and len(income_week) > 0:
                    st.line_chart(income_week.set_index("Weeks")[["Income Produced", "Income Planned"]], use_container_width=True)
                else:
                    st.info("Not enough columns to chart weekly income.")
            else:
                st.info("No Weeks column found after cleaning; weekly trend charts are hidden.")

with tab_orders:
    st.subheader("Open Orders")

    orders_raw = tables.get("Order Status for Angel Report")
    if orders_raw is None:
        st.error("Missing sheet: Order Status for Angel Report")
    else:
        orders_df = _clean_sheet_with_header(orders_raw, required_tokens=["ORDER_NUMBER"])
        if orders_df is None:
            st.error("Could not clean orders sheet")
        else:
            open_orders = np.
            if "ORDER_NUMBER" in orders_df.columns:
                open_orders = int(pd.Series(orders_df["ORDER_NUMBER"]).dropna().nunique())

            open_yards_written = _safe_sum(orders_df, "Yards Written")
            open_income_written = _safe_sum(orders_df, "Income Written")

            d1, d2, d3 = st.columns(3)
            if isinstance(open_orders, float) and np.isnan(open_orders):
                d1.metric("Open Orders", "NA")
            else:
                d1.metric("Open Orders", "{:,}".format(open_orders))
            d2.metric("Open Yards Written", _fmt_num(open_yards_written))
            d3.metric("Open Income Written", _fmt_money(open_income_written))

            st.divider()

            if "Yard Order Status" in orders_df.columns:
                status_counts = (
                    orders_df[["Yard Order Status"]]
                    .dropna()
                    .groupby("Yard Order Status", as_index=False)
                    .size()
                    .sort_values("size", ascending=False)
                )
                st.subheader("Orders by Status (count)")
                st.bar_chart(status_counts.set_index("Yard Order Status")["size"], use_container_width=True)
            else:
                st.info("No Yard Order Status column found after cleaning.")

with tab_debug:
    st.subheader("Debug")

    st.write("Session keys")
    st.write(sorted(list(st.session_state.keys())))

    st.write("Sheet names")
    st.write(sorted(list(tables.keys())))

    ytd_raw_dbg = tables.get("YTD Plan vs Act")
    if ytd_raw_dbg is not None:
        ytd_df_dbg = _clean_sheet_with_header(ytd_raw_dbg, required_tokens=["Weeks", "Yards Produced"])
        st.write("YTD Plan vs Act cleaned head")
        st.dataframe(ytd_df_dbg.head(30), use_container_width=True)
        st.write("YTD columns")
        st.write(list(ytd_df_dbg.columns))

    orders_raw_dbg = tables.get("Order Status for Angel Report")
    if orders_raw_dbg is not None:
        orders_df_dbg = _clean_sheet_with_header(orders_raw_dbg, required_tokens=["ORDER_NUMBER"])
        st.write("Order Status cleaned head")
        st.dataframe(orders_df_dbg.head(30), use_container_width=True)
        st.write("Orders columns")
        st.write(list(orders_df_dbg.columns))
