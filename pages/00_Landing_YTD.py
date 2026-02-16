import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Landing - YTD", layout="wide")

PLAN_PATH = "landing_ytd_plan.parquet"
LY_PATH = "landing_ytd_vs_ly.parquet"

LOCATION_ORDER = ["Brooklyn", "Passaic", "Grand Total"]

def _norm_col(col_name):
    return str(col_name).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(df, candidates):
    df_cols = list(df.columns)
    norm_map = {_norm_col(c): c for c in df_cols}
    for cand in candidates:
        norm_cand = _norm_col(cand)
        if norm_cand in norm_map:
            return norm_map[norm_cand]
    return None

def _safe_num(val):
    try:
        if pd.isna(val):
            return None
        return float(val)
    except Exception:
        return None

def _fmt_money(val):
    num = _safe_num(val)
    if num is None:
        return "-"
    return "${:,.0f}".format(num)

def _fmt_int(val):
    num = _safe_num(val)
    if num is None:
        return "-"
    return "{:,.0f}".format(num)

def _fmt_pct(val):
    num = _safe_num(val)
    if num is None:
        return "-"
    return "{:.1%}".format(num)

@st.cache_data
def load_parquets():
    if (not os.path.exists(PLAN_PATH)) or (not os.path.exists(LY_PATH)):
        return None, None

    plan_df_local = pd.read_parquet(PLAN_PATH)
    ly_df_local = pd.read_parquet(LY_PATH)

    return plan_df_local, ly_df_local

def get_row_for_location(df, location_name):
    if df is None or len(df) == 0:
        return None

    loc_col = _find_col(df, ["Location", "location"])
    if loc_col is None:
        return None

    sub = df[df[loc_col].astype(str).str.strip().str.lower() == str(location_name).strip().lower()]
    if len(sub) == 0:
        return None
    return sub.iloc[0]

def plan_metrics_for_location(plan_df_local, location_name):
    row = get_row_for_location(plan_df_local, location_name)
    if row is None:
        return None

    yards_prod_col = _find_col(plan_df_local, ["Yards Produced", "Produced Yards", "yards_produced"])
    yards_plan_col = _find_col(plan_df_local, ["Yards Planned", "Planned Yards", "yards_planned"])
    income_prod_col = _find_col(plan_df_local, ["Income Produced", "Produced Income", "income_produced"])
    income_plan_col = _find_col(plan_df_local, ["Income Planned", "Planned Income", "income_planned"])
    net_income_inv_col = _find_col(plan_df_local, ["Net Income Invoiced", "Invoiced Income Net", "net_income_invoiced"])
    net_yards_inv_col = _find_col(plan_df_local, ["Net Yards Invoiced", "Invoiced Yards Net", "net_yards_invoiced"])

    yards_prod = row[yards_prod_col] if yards_prod_col is not None else None
    yards_plan = row[yards_plan_col] if yards_plan_col is not None else None
    income_prod = row[income_prod_col] if income_prod_col is not None else None
    income_plan = row[income_plan_col] if income_plan_col is not None else None
    net_income_inv = row[net_income_inv_col] if net_income_inv_col is not None else None
    net_yards_inv = row[net_yards_inv_col] if net_yards_inv_col is not None else None

    yards_delta = None
    income_prod_delta = None
    if _safe_num(yards_prod) is not None and _safe_num(yards_plan) is not None and float(yards_plan) != 0:
        yards_delta = (float(yards_prod) / float(yards_plan)) - 1.0
    if _safe_num(income_prod) is not None and _safe_num(income_plan) is not None and float(income_plan) != 0:
        income_prod_delta = (float(income_prod) / float(income_plan)) - 1.0

    return {
        "yards_produced": yards_prod,
        "yards_planned": yards_plan,
        "yards_vs_plan_pct": yards_delta,
        "income_produced": income_prod,
        "income_planned": income_plan,
        "income_prod_vs_plan_pct": income_prod_delta,
        "net_income_invoiced": net_income_inv,
        "net_yards_invoiced": net_yards_inv
    }

def ly_metrics_for_location(ly_df_local, location_name):
    row = get_row_for_location(ly_df_local, location_name)
    if row is None:
        return None

    written_cur_col = _find_col(ly_df_local, ["Written Current", "Written CY", "written_current"])
    written_ly_col = _find_col(ly_df_local, ["Written LY", "written_ly"])
    produced_cur_col = _find_col(ly_df_local, ["Produced Current", "Produced CY", "produced_current"])
    produced_ly_col = _find_col(ly_df_local, ["Produced LY", "produced_ly"])
    invoiced_cur_col = _find_col(ly_df_local, ["Invoiced Current", "Invoiced CY", "invoiced_current"])
    invoiced_ly_col = _find_col(ly_df_local, ["Invoiced LY", "invoiced_ly"])

    written_cur = row[written_cur_col] if written_cur_col is not None else None
    written_ly = row[written_ly_col] if written_ly_col is not None else None
    produced_cur = row[produced_cur_col] if produced_cur_col is not None else None
    produced_ly = row[produced_ly_col] if produced_ly_col is not None else None
    invoiced_cur = row[invoiced_cur_col] if invoiced_cur_col is not None else None
    invoiced_ly = row[invoiced_ly_col] if invoiced_ly_col is not None else None

    written_vs_ly = None
    produced_vs_ly = None
    invoiced_vs_ly = None

    if _safe_num(written_cur) is not None and _safe_num(written_ly) is not None and float(written_ly) != 0:
        written_vs_ly = (float(written_cur) / float(written_ly)) - 1.0
    if _safe_num(produced_cur) is not None and _safe_num(produced_ly) is not None and float(produced_ly) != 0:
        produced_vs_ly = (float(produced_cur) / float(produced_ly)) - 1.0
    if _safe_num(invoiced_cur) is not None and _safe_num(invoiced_ly) is not None and float(invoiced_ly) != 0:
        invoiced_vs_ly = (float(invoiced_cur) / float(invoiced_ly)) - 1.0

    return {
        "written_current": written_cur,
        "written_ly": written_ly,
        "written_vs_ly_pct": written_vs_ly,
        "produced_current": produced_cur,
        "produced_ly": produced_ly,
        "produced_vs_ly_pct": produced_vs_ly,
        "invoiced_current": invoiced_cur,
        "invoiced_ly": invoiced_ly,
        "invoiced_vs_ly_pct": invoiced_vs_ly
    }

def render_location_section(plan_df_local, ly_df_local, location_name):
    plan_m = plan_metrics_for_location(plan_df_local, location_name)
    ly_m = ly_metrics_for_location(ly_df_local, location_name)

    st.markdown("#### " + location_name)

    if plan_m is None and ly_m is None:
        st.warning("No data found for " + location_name)
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Written**")
        if ly_m is None:
            st.write("-")
        else:
            st.metric(
                label="Income",
                value=_fmt_money(ly_m["written_current"]),
                delta=_fmt_pct(ly_m["written_vs_ly_pct"]) + " vs LY" if ly_m["written_vs_ly_pct"] is not None else None
            )

    with c2:
        st.markdown("**Produced**")
        if plan_m is None and ly_m is None:
            st.write("-")
        else:
            produced_val = None
            produced_delta_txt = None

            if plan_m is not None:
                produced_val = plan_m["income_produced"]
                if plan_m["income_prod_vs_plan_pct"] is not None:
                    produced_delta_txt = _fmt_pct(plan_m["income_prod_vs_plan_pct"]) + " vs Plan"

            if produced_val is None and ly_m is not None:
                produced_val = ly_m["produced_current"]
                if ly_m["produced_vs_ly_pct"] is not None:
                    produced_delta_txt = _fmt_pct(ly_m["produced_vs_ly_pct"]) + " vs LY"

            st.metric(
                label="Income",
                value=_fmt_money(produced_val),
                delta=produced_delta_txt
            )

            if plan_m is not None:
                st.caption(
                    "Yards " + _fmt_int(plan_m["yards_produced"]) +
                    " vs Plan " + _fmt_int(plan_m["yards_planned"]) +
                    " (" + (_fmt_pct(plan_m["yards_vs_plan_pct"]) if plan_m["yards_vs_plan_pct"] is not None else "-") + ")"
                )

    with c3:
        st.markdown("**Invoiced**")
        if plan_m is None and ly_m is None:
            st.write("-")
        else:
            invoiced_val = None
            invoiced_delta_txt = None

            if plan_m is not None:
                invoiced_val = plan_m["net_income_invoiced"]

            if invoiced_val is None and ly_m is not None:
                invoiced_val = ly_m["invoiced_current"]
                if ly_m["invoiced_vs_ly_pct"] is not None:
                    invoiced_delta_txt = _fmt_pct(ly_m["invoiced_vs_ly_pct"]) + " vs LY"

            st.metric(
                label="Net Income",
                value=_fmt_money(invoiced_val),
                delta=invoiced_delta_txt
            )

            if plan_m is not None:
                st.caption("Net Yards " + _fmt_int(plan_m["net_yards_invoiced"]))

def render_page():
    st.title("YTD Scoreboard")
    st.caption("Executive view. Source is generated parquet files built from the workbook on Admin → Data.")

    plan_df_local, ly_df_local = load_parquets()

    if plan_df_local is None or ly_df_local is None:
        st.error("Landing data is not built yet in this environment.")
        st.markdown("Go to **Admin → Data** and run the build step to generate")
        st.code(PLAN_PATH + "\n" + LY_PATH)
        st.stop()

    for loc in LOCATION_ORDER:
        render_location_section(plan_df_local, ly_df_local, loc)
        st.divider()

    with st.expander("Show underlying data (debug)"):
        st.markdown("**Plan vs Act**")
        st.dataframe(plan_df_local, use_container_width=True)
        st.markdown("**Vs LY**")
        st.dataframe(ly_df_local, use_container_width=True)

render_page()
