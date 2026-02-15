import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="YTD", layout="wide")
st.title("YTD")

tables = require_tables()

plan_df, plan_name = get_table(tables, "YTD plan v Actual")
ly_df, ly_name = get_table(tables, "YTD v LY")

if plan_df is None and ly_df is None:
    st.error("Could not find YTD sheets. Check Data page load.")
    st.stop()

def _to_num(s):
    return pd.to_numeric(s, errors="coerce")

def _fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def _fmt_pct(x):
    if x is None:
        return "NA"
    try:
        return "{:.1f}%".format(100.0 * float(x))
    except Exception:
        return "NA"

tab_plan, tab_ly, tab_debug = st.tabs(["Plan vs Actual", "YTD vs LY", "Debug"])

with tab_plan:
    st.subheader("YTD Plan vs Actual")

    if plan_df is None:
        st.info("Missing sheet for Plan vs Actual.")
    else:
        df0 = plan_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]

        metric_col = None
        for c in df0.columns:
            if "metric" in str(c).lower() or "category" in str(c).lower() or "kpi" in str(c).lower():
                metric_col = c
                break
        if metric_col is None:
            metric_col = df0.columns[0]

        plan_col = None
        actual_col = None
        for c in df0.columns:
            c_low = str(c).lower()
            if plan_col is None and "plan" in c_low:
                plan_col = c
            if actual_col is None and ("actual" in c_low or c_low.strip() == "act"):
                actual_col = c

        if actual_col is None:
            for c in df0.columns:
                if "act" in str(c).lower():
                    actual_col = c
                    break

        if plan_col is None or actual_col is None:
            st.warning("Could not confidently detect Plan and Actual columns. See Debug tab.")
            st.dataframe(df0.head(30), use_container_width=True)
        else:
            df1 = df0[[metric_col, plan_col, actual_col]].copy()
            df1[plan_col] = _to_num(df1[plan_col])
            df1[actual_col] = _to_num(df1[actual_col])
            df1["Variance"] = df1[actual_col] - df1[plan_col]
            df1["Attainment"] = df1[actual_col] / df1[plan_col]

            total_plan = float(df1[plan_col].sum(skipna=True))
            total_actual = float(df1[actual_col].sum(skipna=True))
            total_var = total_actual - total_plan
            total_attain = None if total_plan == 0 else total_actual / total_plan

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Plan", _fmt_int(total_plan))
            c2.metric("Total Actual", _fmt_int(total_actual), _fmt_int(total_var))
            c3.metric("Attainment", _fmt_pct(total_attain))

            st.divider()
            st.dataframe(df1.sort_values("Variance", ascending=True), use_container_width=True, hide_index=True)

with tab_ly:
    st.subheader("YTD vs LY")

    if ly_df is None:
        st.info("Missing sheet for YTD vs LY.")
    else:
        df0 = ly_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]

        metric_col = None
        for c in df0.columns:
            if "metric" in str(c).lower() or "category" in str(c).lower() or "kpi" in str(c).lower():
                metric_col = c
                break
        if metric_col is None:
            metric_col = df0.columns[0]

        ytd_col = None
        ly_col = None
        for c in df0.columns:
            c_low = str(c).lower()
            if ytd_col is None and ("ytd" in c_low or "this" in c_low or "ty" in c_low):
                ytd_col = c
            if ly_col is None and ("ly" in c_low or "last" in c_low or "prior" in c_low):
                ly_col = c

        if ytd_col is None:
            for c in df0.columns:
                if "ytd" in str(c).lower():
                    ytd_col = c
                    break

        if ly_col is None:
            for c in df0.columns:
                if "ly" in str(c).lower():
                    ly_col = c
                    break

        if ytd_col is None or ly_col is None:
            st.warning("Could not confidently detect YTD and LY columns. See Debug tab.")
            st.dataframe(df0.head(30), use_container_width=True)
        else:
            df1 = df0[[metric_col, ytd_col, ly_col]].copy()
            df1[ytd_col] = _to_num(df1[ytd_col])
            df1[ly_col] = _to_num(df1[ly_col])
            df1["Delta"] = df1[ytd_col] - df1[ly_col]
            df1["Growth"] = df1["Delta"] / df1[ly_col]

            total_ytd = float(df1[ytd_col].sum(skipna=True))
            total_ly = float(df1[ly_col].sum(skipna=True))
            total_delta = total_ytd - total_ly
            total_growth = None if total_ly == 0 else total_delta / total_ly

            c1, c2, c3 = st.columns(3)
            c1.metric("Total YTD", _fmt_int(total_ytd))
            c2.metric("Total LY", _fmt_int(total_ly), _fmt_int(total_delta))
            c3.metric("Growth", _fmt_pct(total_growth))

            st.divider()
            st.dataframe(df1.sort_values("Delta", ascending=True), use_container_width=True, hide_index=True)

with tab_debug:
    st.subheader("Debug: loaded sources")
    st.write({"plan_sheet": plan_name, "ly_sheet": ly_name})

    if plan_df is not None:
        st.markdown("**Plan vs Actual columns**")
        st.write(list(plan_df.columns))
        st.dataframe(plan_df.head(25), use_container_width=True)

    if ly_df is not None:
        st.markdown("**YTD vs LY columns**")
        st.write(list(ly_df.columns))
        st.dataframe(ly_df.head(25), use_container_width=True)
