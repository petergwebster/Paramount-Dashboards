import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

tables = require_tables()

color_df, color_name = get_table(tables, "Color yds")
wip_df, wip_name = get_table(tables, "WIP")
waste_df, waste_name = get_table(tables, "Yds wasted")

def _to_num(s):
    return pd.to_numeric(s, errors="coerce")

def _fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

tab_overview, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(["Overview", "Color", "WIP", "Waste", "Debug"])

with tab_overview:
    st.subheader("Overview KPIs")

    total_color = None
    if color_df is not None:
        df0 = color_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        num_cols = []
        for c in df0.columns:
            s_num = _to_num(df0[c])
            if s_num.notna().sum() >= max(5, int(0.2 * len(s_num))):
                num_cols.append(c)
        if len(num_cols) > 0:
            total_color = float(_to_num(df0[num_cols[0]]).sum(skipna=True))

    total_wip = None
    if wip_df is not None:
        df0 = wip_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        num_cols = []
        for c in df0.columns:
            s_num = _to_num(df0[c])
            if s_num.notna().sum() >= max(5, int(0.2 * len(s_num))):
                num_cols.append(c)
        if len(num_cols) > 0:
            total_wip = float(_to_num(df0[num_cols[0]]).sum(skipna=True))

    total_waste = None
    if waste_df is not None:
        df0 = waste_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        num_cols = []
        for c in df0.columns:
            s_num = _to_num(df0[c])
            if s_num.notna().sum() >= max(5, int(0.2 * len(s_num))):
                num_cols.append(c)
        if len(num_cols) > 0:
            total_waste = float(_to_num(df0[num_cols[0]]).sum(skipna=True))

    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards (sum)", _fmt_int(total_color))
    c2.metric("WIP (sum)", _fmt_int(total_wip))
    c3.metric("Yards wasted (sum)", _fmt_int(total_waste))

    st.caption("These are quick sums using the first strong numeric column detected per sheet. We can lock to exact columns next.")

with tab_color:
    st.subheader("Color Yards")

    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        df0 = color_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        st.caption("Source sheet: " + str(color_name))
        st.dataframe(df0.head(40), use_container_width=True)

        cat_col = None
        for c in df0.columns:
            if _to_num(df0[c]).notna().sum() < max(5, int(0.1 * len(df0))):
                if df0[c].nunique(dropna=True) > 1 and df0[c].nunique(dropna=True) < 40:
                    cat_col = c
                    break

        num_col = None
        for c in df0.columns:
            if _to_num(df0[c]).notna().sum() >= max(5, int(0.2 * len(df0))):
                num_col = c
                break

        if cat_col is not None and num_col is not None:
            grp = df0[[cat_col, num_col]].copy()
            grp[num_col] = _to_num(grp[num_col])
            grp = grp.dropna(subset=[cat_col])
            grp = grp.groupby(cat_col, as_index=True)[num_col].sum().sort_values(ascending=False).head(20)
            st.bar_chart(grp, use_container_width=True)

with tab_wip:
    st.subheader("WIP")

    if wip_df is None:
        st.info("Missing WIP sheet.")
    else:
        df0 = wip_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        st.caption("Source sheet: " + str(wip_name))
        st.dataframe(df0.head(60), use_container_width=True)

with tab_waste:
    st.subheader("Yards Wasted")

    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        df0 = waste_df.copy()
        df0.columns = [str(c).strip() for c in df0.columns]
        st.caption("Source sheet: " + str(waste_name))
        st.dataframe(df0.head(60), use_container_width=True)

with tab_debug:
    st.subheader("Debug: loaded sources")
    st.write({"color": color_name, "wip": wip_name, "waste": waste_name})

    if color_df is not None:
        st.markdown("**Color Yards columns**")
        st.write(list(color_df.columns))

    if wip_df is not None:
        st.markdown("**WIP columns**")
        st.write(list(wip_df.columns))

    if waste_df is not None:
        st.markdown("**Yards Wasted columns**")
        st.write(list(waste_df.columns))
