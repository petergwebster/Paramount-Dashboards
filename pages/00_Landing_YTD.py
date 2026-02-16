import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Landing - YTD", layout="wide")

PLAN_PATH = "landing_ytd_plan.parquet"
LY_PATH = "landing_ytd_vs_ly.parquet"

LOCATION_ORDER = ["Brooklyn", "Passaic", "Grand Total"]

def _norm_col(col_name):
    return str(col_name).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(df_val, candidates):
    if df_val is None or len(df_val.columns) == 0:
        return None
    norm_map = {_norm_col(c): c for c in df_val.columns}
    for cand in candidates:
        cand_norm = _norm_col(cand)
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None

def _safe_float(val):
    try:
        if pd.isna(val):
            return None
        return float(val)
    except Exception:
        return None

def _fmt_money(val):
    num = _safe_float(val)
    if num is None:
        return "-"
    return "${:,.0f}".format(num)

def _fmt_int(val):
    num = _safe_float(val)
    if num is None:
        return "-"
    return "{:,.0f}".format(num)

def _fmt_pct(val):
    num = _safe_float(val)
    if num is None:
        return "-"
    return "{:.1%}".format(num)

def _calc_vs_plan(actual_val, plan_val):
    actual_num = _safe_float(actual_val)
    plan_num = _safe_float(plan_val)
    if actual_num is None or plan_num is None:
        return None
    if plan_num == 0:
        return None
    return (actual_num - plan_num) / plan_num

def _calc_vs_ly(current_val, ly_val):
    cur_num = _safe_float(current_val)
    ly_num = _safe_float(ly_val)
    if cur_num is None or ly_num is None:
        return None
    if ly_num == 0:
        return None
    return (cur_num - ly_num) / ly_num

@st.cache_data(show_spinner=False)
def _load_landing_parquets_cached(plan_mtime, ly_mtime):
    plan_df_val = pd.read_parquet(PLAN_PATH)
    ly_df_val = pd.read_parquet(LY_PATH)
    return plan_df_val, ly_df_val

def load_landing_parquets():
    plan_exists = os.path.exists(PLAN_PATH)
    ly_exists = os.path.exists(LY_PATH)
    if (not plan_exists) or (not ly_exists):
        return None, None

    plan_mtime = os.path.getmtime(PLAN_PATH)
    ly_mtime = os.path.getmtime(LY_PATH)

    plan_df_val, ly_df_val = _load_landing_parquets_cached(plan_mtime, ly_mtime)
    return plan_df_val, ly_df_val

def _get_row_for_location(df_val, location_name):
    if df_val is None or len(df_val) == 0:
        return None
    loc_col = _find_col(df_val, ["Location"])
    if loc_col is None:
        return None
    sub = df_val[df_val[loc_col].astype(str).str.strip().str.lower() == str(location_name).strip().lower()]
    if len(sub) == 0:
        return None
    return sub.iloc[0]

def _plan_metrics(plan_df_val, location_name):
    row = _get_row_for_location(plan_df_val, location_name)
    if row is None:
        return None

    yards_prod_col = _find_col(plan_df_val, ["Yards Produced", "Produced Yards", "yards_produced"])
    yards_plan_col = _find_col(plan_df_val, ["Yards Planned", "Planned Yards", "yards_planned"])
    income_prod_col = _find_col(plan_df_val, ["Income Produced", "Produced Income", "income_produced"])
    income_plan_col = _find_col(plan_df_val, ["Income Planned", "Planned Income", "income_planned"])
    net_yards_inv_col = _find_col(plan_df_val, ["Net Yards Invoiced", "Invoiced Net Yards", "net_yards_invoiced"])
    net_income_inv_col = _find_col(plan_df_val, ["Net Income Invoiced", "Invoiced Net Income", "net_income_invoiced"])

    yards_prod = row[yards_prod_col] if yards_prod_col is not None else None
    yards_plan = row[yards_plan_col] if yards_plan_col is not None else None
    income_prod = row[income_prod_col] if income_prod_col is not None else None
    income_plan = row[income_plan_col] if income_plan_col is not None else None
    net_yards_inv = row[net_yards_inv_col] if net_yards_inv_col is not None else None
    net_income_inv = row[net_income_inv_col] if net_income_inv_col is not None else None

    return {
        "yards_produced": yards_prod,
        "yards_planned": yards_plan,
        "income_produced": income_prod,
        "income_planned": income_plan,
        "net_yards_invoiced": net_yards_inv,
        "net_income_invoiced": net_income_inv,
        "yards_vs_plan_pct": _calc_vs_plan(yards_prod, yards_plan),
        "income_vs_plan_pct": _calc_vs_plan(income_prod, income_plan),
    }

def _ly_metrics(ly_df_val, location_name):
    row = _get_row_for_location(ly_df_val, location_name)
    if row is None:
        return None

    written_cur_col = _find_col(ly_df_val, ["Written Current", "Written", "Written CY"])
    written_ly_col = _find_col(ly_df_val, ["Written LY", "Written Last Year"])
    produced_cur_col = _find_col(ly_df_val, ["Produced Current", "Produced", "Produced CY"])
    produced_ly_col = _find_col(ly_df_val, ["Produced LY", "Produced Last Year"])
    invoiced_cur_col = _find_col(ly_df_val, ["Invoiced Current", "Invoiced", "Invoiced CY"])
    invoiced_ly_col = _find_col(ly_df_val, ["Invoiced LY", "Invoiced Last Year"])

    written_cur = row[written_cur_col] if written_cur_col is not None else None
    written_ly = row[written_ly_col] if written_ly_col is not None else None
    produced_cur = row[produced_cur_col] if produced_cur_col is not None else None
    produced_ly = row[produced_ly_col] if produced_ly_col is not None else None
    invoiced_cur = row[invoiced_cur_col] if invoiced_cur_col is not None else None
    invoiced_ly = row[invoiced_ly_col] if invoiced_ly_col is not None else None

    return {
        "written_current": written_cur,
        "written_ly": written_ly,
        "produced_current": produced_cur,
        "produced_ly": produced_ly,
        "invoiced_current": invoiced_cur,
        "invoiced_ly": invoiced_ly,
        "written_vs_ly_pct": _calc_vs_ly(written_cur, written_ly),
        "produced_vs_ly_pct": _calc_vs_ly(produced_cur, produced_ly),
        "invoiced_vs_ly_pct": _calc_vs_ly(invoiced_cur, invoiced_ly),
    }

def _render_location_block(plan_df_val, ly_df_val, location_name):
    st.subheader(location_name)

    plan_m = _plan_metrics(plan_df_val, location_name)
    ly_m = _ly_metrics(ly_df_val, location_name)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Written**")
        if ly_m is None:
            st.metric("Income", "-", None)
        else:
            st.metric(
                "Income",
                _fmt_money(ly_m["written_current"]),
                (_fmt_pct(ly_m["written_vs_ly_pct"]) + " vs LY") if ly_m["written_vs_ly_pct"] is not None else None
            )

    with c2:
        st.markdown("**Produced**")
        produced_value = None
        if plan_m is not None and plan_m["income_produced"] is not None:
            produced_value = plan_m["income_produced"]
        elif ly_m is not None:
            produced_value = ly_m["produced_current"]

        produced_delta_parts = []
        if plan_m is not None and plan_m["income_vs_plan_pct"] is not None:
            produced_delta_parts.append(_fmt_pct(plan_m["income_vs_plan_pct"]) + " vs Plan")
        if ly_m is not None and ly_m["produced_vs_ly_pct"] is not None:
            produced_delta_parts.append(_fmt_pct(ly_m["produced_vs_ly_pct"]) + " vs LY")
        produced_delta = " | ".join(produced_delta_parts) if len(produced_delta_parts) > 0 else None

        st.metric("Income", _fmt_money(produced_value), produced_delta)

        if plan_m is not None:
            st.caption(
                "Yards " + _fmt_int(plan_m["yards_produced"]) +
                " vs Plan " + _fmt_int(plan_m["yards_planned"]) +
                " (" + (_fmt_pct(plan_m["yards_vs_plan_pct"]) if plan_m["yards_vs_plan_pct"] is not None else "-") + ")"
            )

    with c3:
        st.markdown("**Invoiced**")
        invoiced_value = None
        if plan_m is not None and plan_m["net_income_invoiced"] is not None:
            invoiced_value = plan_m["net_income_invoiced"]
        elif ly_m is not None:
            invoiced_value = ly_m["invoiced_current"]

        invoiced_delta = None
        if ly_m is not None and ly_m["invoiced_vs_ly_pct"] is not None:
            invoiced_delta = _fmt_pct(ly_m["invoiced_vs_ly_pct"]) + " vs LY"

        st.metric("Net Income", _fmt_money(invoiced_value), invoiced_delta)

        if plan_m is not None and plan_m["net_yards_invoiced"] is not None:
            st.caption("Net Yards " + _fmt_int(plan_m["net_yards_invoiced"]))

def render_page():
    st.title("YTD Scoreboard")
    st.caption("If this page says parquets are missing, go to Admin → Data and click Build Landing parquet files.")

    plan_df_val, ly_df_val = load_landing_parquets()

    if plan_df_val is None or ly_df_val is None:
        st.error("Landing parquet files not found in this environment.")
        st.markdown("Build them in **Admin → Data**, then return here.")
        st.code(PLAN_PATH + "\n" + LY_PATH)
        st.write(PLAN_PATH + " exists: " + str(os.path.exists(PLAN_PATH)))
        st.write(LY_PATH + " exists: " + str(os.path.exists(LY_PATH)))
        st.stop()

    for loc in LOCATION_ORDER:
        _render_location_block(plan_df_val, ly_df_val, loc)
        st.divider()

    with st.expander("Underlying data (debug)", expanded=False):
        st.markdown("**Plan vs Act parquet**")
        st.dataframe(plan_df_val, use_container_width=True)
        st.markdown("**Vs LY parquet**")
        st.dataframe(ly_df_val, use_container_width=True)

render_page()
