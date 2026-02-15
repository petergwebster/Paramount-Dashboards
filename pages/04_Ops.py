import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

tables = require_tables()

color_raw, color_name = get_table(tables, "Color yds")
wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yds wasted")

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

def make_unique_columns(cols):
    seen = {}
    out_cols = []
    for c in cols:
        base = "" if c is None else str(c)
        base = base.strip()
        if base == "" or base.lower() in ["", "none", "nat", "null"]:
            base = "unnamed"
        if base not in seen:
            seen[base] = 0
            out_cols.append(base)
        else:
            seen[base] += 1
            out_cols.append(base + "__" + str(seen[base]))
    return out_cols

def promote_header_row(df_in, header_row_idx):
    df2 = df_in.copy()
    new_cols = df2.iloc[header_row_idx].astype(str).tolist()
    df2.columns = [str(c).strip() for c in new_cols]
    df2 = df2.iloc[header_row_idx + 1 :].reset_index(drop=True)
    return df2

def guess_header_row_ops(df_in, max_scan_rows=25):
    scan_rows = min(max_scan_rows, len(df_in))
    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)
        if "division" in joined and "yards" in joined:
            return i
        if "wip" in joined and "yards" in joined:
            return i
        if "waste" in joined and "yards" in joined:
            return i
    return 0

def quick_sum_first_numeric(df_in):
    if df_in is None or len(df_in) == 0:
        return None, None
    df2 = df_in.copy()
    df2.columns = [str(c).strip() for c in df2.columns]
    for c in list(df2.columns):
        non_na = _to_num(df2[c]).notna().sum()
        if non_na >= max(5, int(0.2 * len(df2))):
            return float(_to_num(df2[c]).sum(skipna=True)), c
    return None, None

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

with tab_dash:
    st.subheader("Ops snapshot")

    color_sum, color_sum_col = quick_sum_first_numeric(color_raw)
    wip_sum, wip_sum_col = quick_sum_first_numeric(wip_raw)
    waste_sum, waste_sum_col = quick_sum_first_numeric(waste_raw)

    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards (sum)", "NA" if color_sum is None else "{:,.0f}".format(color_sum))
    c2.metric("WIP (sum)", "NA" if wip_sum is None else "{:,.0f}".format(wip_sum))
    c3.metric("Yards wasted (sum)", "NA" if waste_sum is None else "{:,.0f}".format(waste_sum))

    st.caption("These are quick sums using the first strong numeric column detected per sheet. Use the Debug tab to lock exact columns later.")

with tab_color:
    st.subheader("Color Yards")

    if color_raw is None:
        st.info("Missing Color Yards sheet.")
    else:
        df0 = color_raw.copy()
        header_row_idx = guess_header_row_ops(df0)
        if header_row_idx > 0:
            df0 = promote_header_row(df0, header_row_idx)
        df0.columns = make_unique_columns(df0.columns)

        st.caption("Source sheet: " + str(color_name))
        st.dataframe(df0.head(60), use_container_width=True)

        cat_col = None
        for c in df0.columns:
            if _to_num(df0[c]).notna().sum() < max(5, int(0.1 * len(df0))):
                if df0[c].nunique(dropna=True) > 1 and df0[c].nunique(dropna=True) < 50:
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
            st.subheader("Top 20")
            st.bar_chart(grp, use_container_width=True)

with tab_wip:
    st.subheader("WIP")

    if wip_raw is None:
        st.info("Missing WIP sheet.")
    else:
        df0 = wip_raw.copy()
        header_row_idx = guess_header_row_ops(df0)
        if header_row_idx > 0:
            df0 = promote_header_row(df0, header_row_idx)
        df0.columns = make_unique_columns(df0.columns)

        st.caption("Source sheet: " + str(wip_name))
        st.dataframe(df0.head(80), use_container_width=True)

with tab_waste:
    st.subheader("Yards Wasted")

    if waste_raw is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        df0 = waste_raw.copy()
        header_row_idx = guess_header_row_ops(df0)
        if header_row_idx > 0:
            df0 = promote_header_row(df0, header_row_idx)
        df0.columns = make_unique_columns(df0.columns)

        st.caption("Source sheet: " + str(waste_name))
        st.dataframe(df0.head(80), use_container_width=True)

with tab_debug:
    st.subheader("Loaded sources")
    st.write(
        {
            "color_sheet": color_name,
            "wip_sheet": wip_name,
            "waste_sheet": waste_name,
        }
    )

    if color_raw is not None:
        st.subheader("Color raw columns")
        st.write(list(color_raw.columns))

    if wip_raw is not None:
        st.subheader("WIP raw columns")
        st.write(list(wip_raw.columns))

    if waste_raw is not None:
        st.subheader("Waste raw columns")
        st.write(list(waste_raw.columns))
