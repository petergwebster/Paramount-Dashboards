import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

tables = require_tables()

color_raw, color_name = get_table(tables, "Color yards")
if color_raw is None:
    color_raw, color_name = get_table(tables, "Color Yards")

wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yards wasted")
if waste_raw is None:
    waste_raw, waste_name = get_table(tables, "Yards Wasted")

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
        if "dept" in joined and "yards" in joined:
            return i
        if "wip" in joined and "yards" in joined:
            return i
        if "waste" in joined and "yards" in joined:
            return i
    return 4

def clean_sheet(df_in):
    if df_in is None:
        return None, None
    df0 = df_in.copy()
    df0.columns = [str(c).strip() for c in df0.columns]
    header_row_idx = guess_header_row_ops(df0)
    if header_row_idx > 0 and header_row_idx < len(df0):
        df0 = promote_header_row(df0, header_row_idx)
    df0.columns = make_unique_columns(df0.columns)
    return df0, header_row_idx

def score_col_for_measure(col_name, sheet_kind):
    name_low = str(col_name).lower()

    score = 0

    if sheet_kind == "color":
        if "color" in name_low:
            score += 3
        if "yards" in name_low:
            score += 4
        if "yd" in name_low:
            score += 1
        if "wip" in name_low or "waste" in name_low:
            score -= 5

    if sheet_kind == "wip":
        if "wip" in name_low:
            score += 5
        if "yards" in name_low or "yd" in name_low:
            score += 3
        if "waste" in name_low:
            score -= 5

    if sheet_kind == "waste":
        if "waste" in name_low or "wasted" in name_low or "scrap" in name_low:
            score += 6
        if "yards" in name_low or "yd" in name_low:
            score += 3
        if "wip" in name_low:
            score -= 5

    if "total" in name_low:
        score += 1
    if "income" in name_low or "cost" in name_low or "rate" in name_low or "%" in name_low:
        score -= 2

    return score

def pick_measure_col(df0, sheet_kind):
    if df0 is None:
        return None

    best_col = None
    best_score = -10**9

    for c in list(df0.columns):
        score = score_col_for_measure(c, sheet_kind)

        num_series = _to_num(df0[c])
        non_null_num = int(num_series.notna().sum())
        if non_null_num < max(5, int(0.15 * len(df0))):
            score -= 3
        else:
            score += 2

        if num_series.abs().sum(skipna=True) == 0:
            score -= 2

        if score > best_score:
            best_score = score
            best_col = c

    return best_col

def fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

def sheet_sum(df0, col_name):
    if df0 is None or col_name is None:
        return None
    vals = _to_num(df0[col_name])
    if vals.notna().sum() == 0:
        return None
    return float(vals.sum(skipna=True))

color_df, color_header_idx = clean_sheet(color_raw)
wip_df, wip_header_idx = clean_sheet(wip_raw)
waste_df, waste_header_idx = clean_sheet(waste_raw)

color_measure_col = pick_measure_col(color_df, "color")
wip_measure_col = pick_measure_col(wip_df, "wip")
waste_measure_col = pick_measure_col(waste_df, "waste")

color_total = sheet_sum(color_df, color_measure_col)
wip_total = sheet_sum(wip_df, wip_measure_col)
waste_total = sheet_sum(waste_df, waste_measure_col)

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

with tab_dash:
    st.subheader("Ops snapshot (locked columns)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards (sum)", fmt_int(color_total))
    c2.metric("WIP (sum)", fmt_int(wip_total))
    c3.metric("Yards wasted (sum)", fmt_int(waste_total))

    st.caption(
        "These sums are now using explicitly selected columns per sheet, not the first numeric column."
    )

with tab_color:
    st.subheader("Color Yards")
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        st.caption("Source sheet: " + str(color_name) + " | Header promoted from row: " + str(color_header_idx))
        st.write({"locked_measure_col": color_measure_col})
        st.dataframe(color_df.head(80), use_container_width=True)

with tab_wip:
    st.subheader("WIP")
    if wip_df is None:
        st.info("Missing WIP sheet.")
    else:
        st.caption("Source sheet: " + str(wip_name) + " | Header promoted from row: " + str(wip_header_idx))
        st.write({"locked_measure_col": wip_measure_col})
        st.dataframe(wip_df.head(80), use_container_width=True)

with tab_waste:
    st.subheader("Yards Wasted")
    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        st.caption("Source sheet: " + str(waste_name) + " | Header promoted from row: " + str(waste_header_idx))
        st.write({"locked_measure_col": waste_measure_col})
        st.dataframe(waste_df.head(80), use_container_width=True)

with tab_debug:
    st.subheader("Chosen columns")
    st.write(
        {
            "color_sheet": color_name,
            "color_header_row_idx": color_header_idx,
            "color_measure_col": color_measure_col,
            "wip_sheet": wip_name,
            "wip_header_row_idx": wip_header_idx,
            "wip_measure_col": wip_measure_col,
            "waste_sheet": waste_name,
            "waste_header_row_idx": waste_header_idx,
            "waste_measure_col": waste_measure_col,
        }
    )

    if color_df is not None and color_measure_col is not None:
        st.subheader("Color measure column value counts (top 20 non-null)")
        st.write(_to_num(color_df[color_measure_col]).dropna().head(20))

    if wip_df is not None and wip_measure_col is not None:
        st.subheader("WIP measure column value counts (top 20 non-null)")
        st.write(_to_num(wip_df[wip_measure_col]).dropna().head(20))

    if waste_df is not None and waste_measure_col is not None:
        st.subheader("Waste measure column value counts (top 20 non-null)")
        st.write(_to_num(waste_df[waste_measure_col]).dropna().head(20))
