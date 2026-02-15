import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")

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
    return "{:,.0f}".format(float(x))

def _fmt_money(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return "${:,.0f}".format(float(x))

def _fmt_pct(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return "{:.1f}%".format(float(x) * 100.0)

tables, source_key = _get_sheets_dict_from_session()

if tables is None:
    st.warning("No sheets dict found in session. Go to Data page and click the load button, then return here.")
    st.subheader("Debug session_state keys")
    st.write(sorted(list(st.session_state.keys())))
    st.stop()

st.caption("Using sheets from st.session_state[" + source_key + "]")

tab_kpis, tab_orders, tab_debug = st.tabs(["KPIs", "Orders", "Debug"])

with tab_kpis:
    st.subheader("YTD Plan vs Actual")

    ytd_raw = tables.get("YTD Plan vs Act")
    if ytd_raw is None:
        st.error("Missing sheet: YTD Plan vs Act")
    else:
        ytd_df = _clean_sheet_with_header(ytd_raw, required_tokens=["Weeks", "Yards Produced"])

        if "Weeks" in ytd_df.columns:
            ytd_df["Weeks_num"] = _to_num(ytd_df["Weeks"])
            ytd_df = ytd_df.sort_values("Weeks_num")

        yards_plan = _safe_sum(ytd_df, "Yards Produced Plan")
        yards_act = _safe_sum(ytd_df, "Yards Produced Actual")
        inc_plan = _safe_sum(ytd_df, "Income Produced Plan")
        inc_act = _safe_sum(ytd_df, "Income Produced Actual")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Yards Plan", _fmt_num(yards_plan))
        c2.metric("Yards Actual", _fmt_num(yards_act))
        c3.metric("Income Plan", _fmt_money(inc_plan))
        c4.metric("Income Actual", _fmt_money(inc_act))

        st.divider()

        if "Weeks_num" in ytd_df.columns and "Yards Produced Actual" in ytd_df.columns:
            chart_df = ytd_df[["Weeks_num", "Yards Produced Plan", "Yards Produced Actual"]].copy()
            for col in ["Yards Produced Plan", "Yards Produced Actual"]:
                if col in chart_df.columns:
                    chart_df[col] = _to_num(chart_df[col])
            chart_df = chart_df.dropna(subset=["Weeks_num"])
            chart_df = chart_df.set_index("Weeks_num")
            st.line_chart(chart_df, use_container_width=True)
        else:
            st.info("Could not build chart: missing Weeks and/or Yards columns after cleaning.")

with tab_orders:
    st.subheader("Open Orders Summary")

    orders_raw = tables.get("Order Status for Angel Report")
    if orders_raw is None:
        st.error("Missing sheet: Order Status for Angel Report")
    else:
        orders_df = _clean_sheet_with_header(orders_raw, required_tokens=["ORDER_NUMBER"])

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
        st.write("YTD cleaned head")
        st.dataframe(ytd_df_dbg.head(25), use_container_width=True)
        st.write("YTD columns")
        st.write(list(ytd_df_dbg.columns))

    orders_raw_dbg = tables.get("Order Status for Angel Report")
    if orders_raw_dbg is not None:
        orders_df_dbg = _clean_sheet_with_header(orders_raw_dbg, required_tokens=["ORDER_NUMBER"])
        st.write("Orders cleaned head")
        st.dataframe(orders_df_dbg.head(25), use_container_width=True)
        st.write("Orders columns")
        st.write(list(orders_df_dbg.columns))
