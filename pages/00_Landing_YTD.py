import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Landing - YTD", layout="wide")

PLAN_PATH = "landing_ytd_plan.parquet"
LY_PATH = "landing_ytd_vs_ly.parquet"

EXCLUDE_LOCATIONS = {
    "design services",
    "design services total",
}

TOTAL_LIKE = {
    "grand total",
    "total",
    "overall",
    "company total",
    "all",
}


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


def _calc_pct_change(new_val, base_val):
    new_num = _safe_float(new_val)
    base_num = _safe_float(base_val)
    if new_num is None or base_num is None:
        return None
    if base_num == 0:
        return None
    return (new_num - base_num) / base_num


def _norm_loc(loc_val):
    if loc_val is None:
        return None
    if pd.isna(loc_val):
        return None
    loc_str = str(loc_val).strip()
    if loc_str == "":
        return None
    if loc_str.lower() == "":
        return None
    return loc_str


def _find_col(df_val, candidates):
    if df_val is None or len(df_val.columns) == 0:
        return None

    norm_map = {}
    for c in df_val.columns:
        key = str(c).strip().lower().replace(" ", "_").replace("-", "_")
        norm_map[key] = c

    for cand in candidates:
        cand_key = str(cand).strip().lower().replace(" ", "_").replace("-", "_")
        if cand_key in norm_map:
            return norm_map[cand_key]

    return None


@st.cache_data(show_spinner=False)
def _load_parquets_cached(plan_mtime, ly_mtime):
    plan_df_val = pd.read_parquet(PLAN_PATH)
    ly_df_val = pd.read_parquet(LY_PATH)

    for df_val in [plan_df_val, ly_df_val]:
        if "Location" in df_val.columns:
            df_val["Location"] = df_val["Location"].apply(_norm_loc)

    return plan_df_val, ly_df_val


def load_parquets():
    if not os.path.exists(PLAN_PATH) or not os.path.exists(LY_PATH):
        return None, None

    plan_mtime = os.path.getmtime(PLAN_PATH)
    ly_mtime = os.path.getmtime(LY_PATH)

    plan_df_val, ly_df_val = _load_parquets_cached(plan_mtime, ly_mtime)
    return plan_df_val, ly_df_val


def _locations_from_df(df_val):
    if df_val is None or "Location" not in df_val.columns:
        return []

    locs = (
        df_val["Location"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    locs = locs[~locs.str.lower().isin(["", ""])]
    locs = locs[~locs.str.lower().isin(EXCLUDE_LOCATIONS)]
    return sorted(locs.unique().tolist())


def _compute_location_order(plan_df_val, ly_df_val):
    all_locs = sorted(list(set(_locations_from_df(plan_df_val) + _locations_from_df(ly_df_val))))

    totals = [x for x in all_locs if str(x).strip().lower() in TOTAL_LIKE]
    non_totals = [x for x in all_locs if x not in totals]

    return non_totals + totals


def _row_for_location(df_val, loc_name):
    if df_val is None or len(df_val) == 0:
        return None
    if "Location" not in df_val.columns:
        return None

    sub = df_val[df_val["Location"].astype(str).str.strip().str.lower() == str(loc_name).strip().lower()]
    if len(sub) == 0:
        return None
    return sub.iloc[0]


def _plan_metrics(plan_df_val, loc_name):
    row = _row_for_location(plan_df_val, loc_name)
    if row is None:
        return None

    yards_prod_col = _find_col(plan_df_val, ["Yards Produced"])
    yards_plan_col = _find_col(plan_df_val, ["Yards Planned"])
    income_prod_col = _find_col(plan_df_val, ["Income Produced"])
    income_plan_col = _find_col(plan_df_val, ["Income Planned"])
    net_yards_inv_col = _find_col(plan_df_val, ["Net Yards Invoiced"])
    net_income_inv_col = _find_col(plan_df_val, ["Net Income Invoiced"])

    yards_produced = row.get(yards_prod_col, None) if yards_prod_col else None
    yards_planned = row.get(yards_plan_col, None) if yards_plan_col else None
    income_produced = row.get(income_prod_col, None) if income_prod_col else None
    income_planned = row.get(income_plan_col, None) if income_plan_col else None
    net_yards_invoiced = row.get(net_yards_inv_col, None) if net_yards_inv_col else None
    net_income_invoiced = row.get(net_income_inv_col, None) if net_income_inv_col else None

    return {
        "yards_produced": yards_produced,
        "yards_planned": yards_planned,
        "income_produced": income_produced,
        "income_planned": income_planned,
        "net_yards_invoiced": net_yards_invoiced,
        "net_income_invoiced": net_income_invoiced,
        "yards_vs_plan_pct": _calc_pct_change(yards_produced, yards_planned),
        "income_vs_plan_pct": _calc_pct_change(income_produced, income_planned),
    }


def _ly_metrics(ly_df_val, loc_name):
    row = _row_for_location(ly_df_val, loc_name)
    if row is None:
        return None

    produced_cur_col = _find_col(ly_df_val, ["Produced Current", "Income Produced Current", "Produced"])
    produced_ly_col = _find_col(ly_df_val, ["Produced LY", "Income Produced LY", "Produced Last Year"])
    written_cur_col = _find_col(ly_df_val, ["Written Current", "Written"])
    written_ly_col = _find_col(ly_df_val, ["Written LY", "Written Last Year"])
    invoiced_cur_col = _find_col(ly_df_val, ["Invoiced Current", "Net Income Invoiced Current", "Invoiced"])
    invoiced_ly_col = _find_col(ly_df_val, ["Invoiced LY", "Net Income Invoiced LY", "Invoiced Last Year"])

    produced_current = row.get(produced_cur_col, None) if produced_cur_col else None
    produced_ly = row.get(produced_ly_col, None) if produced_ly_col else None
    written_current = row.get(written_cur_col, None) if written_cur_col else None
    written_ly = row.get(written_ly_col, None) if written_ly_col else None
    invoiced_current = row.get(invoiced_cur_col, None) if invoiced_cur_col else None
    invoiced_ly = row.get(invoiced_ly_col, None) if invoiced_ly_col else None

    return {
        "produced_current": produced_current,
        "produced_ly": produced_ly,
        "written_current": written_current,
        "written_ly": written_ly,
        "invoiced_current": invoiced_current,
        "invoiced_ly": invoiced_ly,
        "produced_vs_ly_pct": _calc_pct_change(produced_current, produced_ly),
        "written_vs_ly_pct": _calc_pct_change(written_current, written_ly),
        "invoiced_vs_ly_pct": _calc_pct_change(invoiced_current, invoiced_ly),
    }


def _render_location_block(plan_df_val, ly_df_val, loc_name):
    plan_m = _plan_metrics(plan_df_val, loc_name)
    ly_m = _ly_metrics(ly_df_val, loc_name)

    st.subheader(loc_name)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Written**")
        written_value = ly_m["written_current"] if ly_m is not None else None
        written_delta = (_fmt_pct(ly_m["written_vs_ly_pct"]) + " vs LY") if (ly_m is not None and ly_m["written_vs_ly_pct"] is not None) else None
        st.metric("Income", _fmt_money(written_value), written_delta)

    with c2:
        st.markdown("**Produced**")
        produced_value = None
        produced_delta_parts = []

        if plan_m is not None and plan_m["income_produced"] is not None:
            produced_value = plan_m["income_produced"]
        elif ly_m is not None:
            produced_value = ly_m["produced_current"]

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
        invoiced_delta = None

        if plan_m is not None and plan_m["net_income_invoiced"] is not None:
            invoiced_value = plan_m["net_income_invoiced"]
        elif ly_m is not None:
            invoiced_value = ly_m["invoiced_current"]

        if ly_m is not None and ly_m["invoiced_vs_ly_pct"] is not None:
            invoiced_delta = _fmt_pct(ly_m["invoiced_vs_ly_pct"]) + " vs LY"

        st.metric("Net Income", _fmt_money(invoiced_value), invoiced_delta)

        if plan_m is not None and plan_m["net_yards_invoiced"] is not None:
            st.caption("Net Yards " + _fmt_int(plan_m["net_yards_invoiced"]))


def render_page():
    st.title("YTD Scoreboard")

    plan_df_val, ly_df_val = load_parquets()

    if plan_df_val is None or ly_df_val is None:
        st.error("Landing parquet files not found.")
        st.markdown("Go to **Admin → Data** and click **Build Landing parquet files**.")
        st.code(PLAN_PATH + "\n" + LY_PATH)
        st.write(PLAN_PATH + " exists: " + str(os.path.exists(PLAN_PATH)))
        st.write(LY_PATH + " exists: " + str(os.path.exists(LY_PATH)))
        st.stop()

    location_order = _compute_location_order(plan_df_val, ly_df_val)

    if len(location_order) == 0:
        st.error("No locations found in parquet files after filtering.")
        with st.expander("Debug", expanded=True):
            st.dataframe(plan_df_val.head(50), use_container_width=True)
            st.dataframe(ly_df_val.head(50), use_container_width=True)
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
