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


@st.cache_data(show_spinner=False)
def load_landing_parquets():
    if (not os.path.exists(PLAN_PATH)) or (not os.path.exists(LY_PATH)):
        return None, None
    plan_df_val = pd.read_parquet(PLAN_PATH)
    ly_df_val = pd.read_parquet(LY_PATH)
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


def _get_plan_metrics(plan_df_val, location_name):
    row = _get_row_for_location(plan_df_val, location_name)
    if row is None:
        return None

    loc_col = _find_col(plan_df_val, ["Location"])

    yards_prod_col = _find_col(plan_df_val, ["Yards Produced", "Produced Yards", "yards_produced"])
    yards_plan_col = _find_col(plan_df_val, ["Yards Planned", "Planned Yards", "yards_planned"])

    income_prod_col = _find_col(plan_df_val, ["Income Produced", "Produced Income", "income_produced"])
    income_plan_col = _find_col(plan_df_val, ["Income Planned", "Planned Income", "income_planned"])

    net_yards_inv_col = _find_col(plan_df_val, ["Net Yards Invoiced", "Invoiced Net Yards", "net_yards_invoiced"])
    net_income_inv_col = _find_col(plan_df_val, ["Net Income Invoiced", "Invoiced Net Income", "net_income_invoiced"])

    out = {"Location": row[loc_col] if loc_col is not None else location_name}

    out["yards_produced"] = row[yards_prod_col] if yards_prod_col is not None else None
    out["yards_planned"] = row[yards_plan_col] if yards_plan_col is not None else None
    out["yards_vs_plan_pct"] = _calc_vs_plan(out["yards_produced"], out["yards_planned"])

    out["income_produced"] = row[income_prod_col] if income_prod_col is not None else None
    out["income_planned"] = row[income_plan_col] if income_plan_col is not None else None
    out["income_vs_plan_pct"] = _calc_vs_plan(out["income_produced"], out["income_planned"])

    out["net_yards_invoiced"] = row[net_yards_inv_col] if net_yards_inv_col is not None else None
    out["net_income_invoiced"] = row[net_income_inv_col] if net_income_inv_col is not None else None

    return out


def _get_ly_metrics(ly_df_val, location_name):
    row = _get_row_for_location(ly_df_val, location_name)
    if row is None:
        return None

    loc_col = _find_col(ly_df_val, ["Location"])

    written_cur_col = _find_col(ly_df_val, ["Written Current", "Written", "Written CY", "written_current"])
    written_ly_col = _find_col(ly_df_val, ["Written LY", "written_ly"])

    produced_cur_col = _find_col(ly_df_val, ["Produced Current", "Produced", "Produced CY", "produced_current"])
    produced_ly_col = _find_col(ly_df_val, ["Produced LY", "produced_ly"])

    invoiced_cur_col = _find_col(ly_df_val, ["Invoiced Current", "Invoiced", "Invoiced CY", "invoiced_current"])
    invoiced_ly_col = _find_col(ly_df_val, ["Invoiced LY", "invoiced_ly"])

    out = {"Location": row[loc_col] if loc_col is not None else location_name}

    out["written_current"] = row[written_cur_col] if written_cur_col is not None else None
    out["written_ly"] = row[written_ly_col] if written_ly_col is not None else None
    out["written_vs_ly_pct"] = _calc_vs_ly(out["written_current"], out["written_ly"])

    out["produced_current"] = row[produced_cur_col] if produced_cur_col is not None else None
    out["produced_ly"] = row[produced_ly_col] if produced_ly_col is not None else None
    out["produced_vs_ly_pct"] = _calc_vs_ly(out["produced_current"], out["produced_ly"])

    out["invoiced_current"] = row[invoiced_cur_col] if invoiced_cur_col is not None else None
    out["invoiced_ly"] = row[invoiced_ly_col] if invoiced_ly_col is not None else None
    out["invoiced_vs_ly_pct"] = _calc_vs_ly(out["invoiced_current"], out["invoiced_ly"])

    return out


def _render_location_block(plan_df_val, ly_df_val, location_name):
    plan_m = _get_plan_metrics(plan_df_val, location_name)
    ly_m = _get_ly_metrics(ly_df_val, location_name)

    st.subheader(location_name)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Written**")
        if ly_m is None:
            st.metric("Income", "-", None)
            st.caption("No LY data found for this location")
        else:
            st.metric(
                "Income",
                _fmt_money(ly_m["written_current"]),
                (_fmt_pct(ly_m["written_vs_ly_pct"]) + " vs LY") if ly_m["written_vs_ly_pct"] is not None else None
            )
            if ly_m["written_ly"] is not None:
                st.caption("LY " + _fmt_money(ly_m["written_ly"]))

    with c2:
        st.markdown("**Produced**")
        produced_value = plan_m["income_produced"] if plan_m is not None else (ly_m["produced_current"] if ly_m is not None else None)

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
        invoiced_value = plan_m["net_income_invoiced"] if plan_m is not None else (ly_m["invoiced_current"] if ly_m is not None else None)

        invoiced_delta_parts = []
        if ly_m is not None and ly_m["invoiced_vs_ly_pct"] is not None:
            invoiced_delta_parts.append(_fmt_pct(ly_m["invoiced_vs_ly_pct"]) + " vs LY")
        invoiced_delta = " | ".join(invoiced_delta_parts) if len(invoiced_delta_parts) > 0 else None

        st.metric("Net Income", _fmt_money(invoiced_value), invoiced_delta)

        if plan_m is not None and plan_m["net_yards_invoiced"] is not None:
            st.caption("Net Yards " + _fmt_int(plan_m["net_yards_invoiced"]))


def render_page():
    st.title("YTD Scoreboard")
    st.caption("If this page is blank or errors, go to Admin → Data and rebuild the landing parquet files.")

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
