import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Landing - YTD", layout="wide")

PLAN_PATH = "landing_ytd_plan.parquet"
LY_PATH = "landing_ytd_vs_ly.parquet"


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
    if (not os.path.exists(PLAN_PATH)) or (not os.path.exists(LY_PATH)):
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


def _get_plan_metrics(plan_df_val, location_name):
    row = _get_row_for_location(plan_df_val, location_name)
    if row is None:
        return None

    yards_produced = row.get("Yards Produced", None)
    yards_planned = row.get("Yards Planned", None)
    income_produced = row.get("Income Produced", None)
    income_planned = row.get("Income Planned", None)
    net_yards_invoiced = row.get("Net Yards Invoiced", None)
    net_income_invoiced = row.get("Net Income Invoiced", None)

    return {
        "yards_produced": yards_produced,
        "yards_planned": yards_planned,
        "income_produced": income_produced,
        "income_planned": income_planned,
        "net_yards_invoiced": net_yards_invoiced,
        "net_income_invoiced": net_income_invoiced,
        "yards_vs_plan_pct": _calc_vs_plan(yards_produced, yards_planned),
        "income_vs_plan_pct": _calc_vs_plan(income_produced, income_planned),
    }


def _get_ly_metrics(ly_df_val, location_name):
    row = _get_row_for_location(ly_df_val, location_name)
    if row is None:
        return None

    written_current = row.get("Written Current", None)
    written_ly = row.get("Written LY", None)
    produced_current = row.get("Produced Current", None)
    produced_ly = row.get("Produced LY", None)
    invoiced_current = row.get("Invoiced Current", None)
    invoiced_ly = row.get("Invoiced LY", None)

    return {
        "written_current": written_current,
        "written_ly": written_ly,
        "produced_current": produced_current,
        "produced_ly": produced_ly,
        "invoiced_current": invoiced_current,
        "invoiced_ly": invoiced_ly,
        "written_vs_ly_pct": _calc_vs_ly(written_current, written_ly),
        "produced_vs_ly_pct": _calc_vs_ly(produced_current, produced_ly),
        "invoiced_vs_ly_pct": _calc_vs_ly(invoiced_current, invoiced_ly),
    }


def _locations_from_df(df_val):
    if df_val is None or "Location" not in df_val.columns:
        return []
    locs = (
        df_val["Location"]
        .astype(str)
        .str.strip()
        .replace({"": None})
        .dropna()
        .unique()
        .tolist()
    )
    return locs


def _compute_location_order(plan_df_val, ly_df_val):
    all_locs = sorted(list(set(_locations_from_df(plan_df_val) + _locations_from_df(ly_df_val))))
    totals = [x for x in all_locs if str(x).strip().lower() in ["grand total", "total", "overall", "company total"]]
    non_totals = [x for x in all_locs if x not in totals]
    return non_totals + totals


def _render_location_block(plan_df_val, ly_df_val, location_name):
    st.subheader(str(location_name))

    plan_m = _get_plan_metrics(plan_df_val, location_name)
    ly_m = _get_ly_metrics(ly_df_val, location_name)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Written**")
        written_value = ly_m["written_current"] if ly_m is not None else None
        written_delta = None
        if ly_m is not None and ly_m["written_vs_ly_pct"] is not None:
            written_delta = _fmt_pct(ly_m["written_vs_ly_pct"]) + " vs LY"
        st.metric("Income", _fmt_money(written_value), written_delta)

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

    plan_df_val, ly_df_val = load_landing_parquets()

    if plan_df_val is None or ly_df_val is None:
        st.error("Landing parquet files not found.")
        st.markdown("Go to **Admin → Data** and click **Build Landing parquet files**.")
        st.code(PLAN_PATH + "\n" + LY_PATH)
        st.write(PLAN_PATH + " exists: " + str(os.path.exists(PLAN_PATH)))
        st.write(LY_PATH + " exists: " + str(os.path.exists(LY_PATH)))
        st.stop()

    location_order = _compute_location_order(plan_df_val, ly_df_val)
    if len(location_order) == 0:
        st.error("No locations found in parquet files.")
        with st.expander("Debug data", expanded=True):
            st.dataframe(plan_df_val, use_container_width=True)
            st.dataframe(ly_df_val, use_container_width=True)
        st.stop()

    for loc in location_order:
        _render_location_block(plan_df_val, ly_df_val, loc)
        st.divider()

    with st.expander("Underlying data (debug)", expanded=False):
        st.markdown("**Plan vs Act parquet**")
        st.dataframe(plan_df_val, use_container_width=True)
        st.markdown("**Vs LY parquet**")
        st.dataframe(ly_df_val, use_container_width=True)


render_page()
