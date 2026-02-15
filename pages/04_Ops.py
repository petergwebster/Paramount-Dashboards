import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

tables = require_tables()

color_raw, color_name = get_table(tables, "Color Yards")
wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yards Wasted")

def _to_num(series_in):
    series_as_str = series_in.astype(str)
    series_as_str = series_as_str.str.replace(",", "", regex=False)
    series_as_str = series_as_str.str.replace("\u00a0", " ", regex=False)
    series_as_str = series_as_str.str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
    return pd.to_numeric(series_as_str, errors="coerce")

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

def guess_header_row(df_in, max_scan_rows=40):
    if df_in is None or len(df_in) == 0:
        return 0

    scan_rows = min(max_scan_rows, len(df_in))
    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)

        if "total yards held to invoice" in joined:
            return i
        if "total wasted yards" in joined:
            return i
        if "yards" in joined and ("division" in joined or "dept" in joined or "department" in joined):
            return i
        if "yards" in joined:
            return i

    return 0

def clean_sheet(df_raw_in, header_idx):
    if df_raw_in is None:
        return None
    df0 = df_raw_in.copy()
    df0.columns = [str(c).strip() for c in df0.columns]
    df0 = promote_header_row(df0, header_idx)
    df0.columns = make_unique_columns(df0.columns)
    return df0

def is_code_like_header(col_name):
    name_low = str(col_name).strip().lower()
    if name_low.startswith("unnamed"):
        return True
    if "__" in name_low:
        left = name_low.split("__")[0]
        if left.replace(".", "", 1).isdigit():
            return True
    if name_low.replace(".", "", 1).isdigit():
        return True
    return False

def pick_measure_col(df_in, exact=None, prefer_keywords=None, avoid_code_like=False):
    if df_in is None:
        return None

    if exact is not None and exact in df_in.columns:
        return exact

    if prefer_keywords is None:
        prefer_keywords = []

    cols = list(df_in.columns)
    if len(cols) == 0:
        return None

    def score_col(c):
        name_low = str(c).strip().lower()
        score = 0

        if name_low in ["", "", "none", "nat", "null", "unnamed"]:
            score -= 50
        if avoid_code_like and is_code_like_header(c):
            score -= 40

        for kw in prefer_keywords:
            if kw in name_low:
                score += 25

        if "%" in name_low or "percent" in name_low or "rate" in name_low:
            score -= 15

        nn = int(_to_num(df_in[c]).notna().sum())
        score += min(35, nn)

        return score

    scored = sorted([(c, score_col(c)) for c in cols], key=lambda x: x[1], reverse=True)
    best_col = scored[0][0]
    best_score = scored[0][1]

    if best_score <= 0:
        return None

    return best_col

def pick_color_measure_col(color_df):
    if color_df is None:
        return None

    yard_cols = []
    for c in color_df.columns:
        name_low = str(c).lower()
        if "yard" in name_low and not is_code_like_header(c):
            yard_cols.append(c)

    if len(yard_cols) == 0:
        return pick_measure_col(
            color_df,
            exact=None,
            prefer_keywords=["yard", "yards", "color"],
            avoid_code_like=True,
        )

    best_col = None
    best_nn = -1
    for c in yard_cols:
        nn = int(_to_num(color_df[c]).notna().sum())
        if nn > best_nn:
            best_nn = nn
            best_col = c

    return best_col

def sum_measure(df_in, measure_col):
    if df_in is None or measure_col is None or measure_col not in df_in.columns:
        return None
    return float(_to_num(df_in[measure_col]).sum(skipna=True))

def top_value_counts(df_in, col_name, top_n=20):
    if df_in is None or col_name is None or col_name not in df_in.columns:
        return None
    s = df_in[col_name].astype(str).str.replace("\u00a0", " ", regex=False).str.strip().str.lower()
    return s.value_counts(dropna=False).head(top_n)

def numeric_strength(df_in, top_n=15):
    if df_in is None:
        return None
    rows = []
    for c in df_in.columns:
        rows.append({"col": c, "non_null_numeric": int(_to_num(df_in[c]).notna().sum())})
    return pd.DataFrame(rows).sort_values("non_null_numeric", ascending=False).head(top_n)

def fmt_int(x):
    if x is None:
        return "NA"
    try:
        return "{:,.0f}".format(float(x))
    except Exception:
        return "NA"

color_header_idx = guess_header_row(color_raw)
wip_header_idx = guess_header_row(wip_raw)
waste_header_idx = guess_header_row(waste_raw)

color_df = clean_sheet(color_raw, color_header_idx)
wip_df = clean_sheet(wip_raw, wip_header_idx)
waste_df = clean_sheet(waste_raw, waste_header_idx)

color_measure_col = pick_color_measure_col(color_df)
wip_measure_col = pick_measure_col(wip_df, exact="Total Yards Held to Invoice", prefer_keywords=["held", "invoice", "yard", "wip"])
waste_measure_col = pick_measure_col(waste_df, exact="Total Wasted Yards", prefer_keywords=["waste", "wasted", "yard", "scrap"])

color_total = sum_measure(color_df, color_measure_col)
wip_total = sum_measure(wip_df, wip_measure_col)
waste_total = sum_measure(waste_df, waste_measure_col)

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

with tab_dash:
    st.subheader("Ops snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards (sum)", fmt_int(color_total))
    c2.metric("WIP yards (sum)", fmt_int(wip_total))
    c3.metric("Yards wasted (sum)", fmt_int(waste_total))

    st.caption("These KPIs are sums of locked measure columns per sheet. Use Debug to see exactly which column was selected.")

with tab_color:
    st.subheader("Color Yards")
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        st.caption("Source sheet: " + str(color_name) + " | Header promoted from row: " + str(color_header_idx))
        st.write({"color_measure_col": color_measure_col})
        st.dataframe(color_df.head(80), use_container_width=True)

with tab_wip:
    st.subheader("WIP")
    if wip_df is None:
        st.info("Missing WIP sheet.")
    else:
        st.caption("Source sheet: " + str(wip_name) + " | Header promoted from row: " + str(wip_header_idx))
        st.write({"wip_measure_col": wip_measure_col})
        st.dataframe(wip_df.head(80), use_container_width=True)

with tab_waste:
    st.subheader("Yards Wasted")
    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        st.caption("Source sheet: " + str(waste_name) + " | Header promoted from row: " + str(waste_header_idx))
        st.write({"waste_measure_col": waste_measure_col})
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

    st.markdown("### Color debug")
    if color_df is None:
        st.info("No Color dataframe loaded.")
    else:
        st.markdown("#### Numeric strength")
        st.dataframe(numeric_strength(color_df, top_n=15), use_container_width=True)

        st.markdown("#### Measure column value counts (top 20)")
        st.write(top_value_counts(color_df, color_measure_col, top_n=20))

    st.markdown("### WIP debug")
    if wip_df is None:
        st.info("No WIP dataframe loaded.")
    else:
        st.markdown("#### Numeric strength")
        st.dataframe(numeric_strength(wip_df, top_n=15), use_container_width=True)

        st.markdown("#### Measure column value counts (top 20)")
        st.write(top_value_counts(wip_df, wip_measure_col, top_n=20))

    st.markdown("### Waste debug")
    if waste_df is None:
        st.info("No Waste dataframe loaded.")
    else:
        st.markdown("#### Numeric strength")
        st.dataframe(numeric_strength(waste_df, top_n=15), use_container_width=True)

        st.markdown("#### Measure column value counts (top 20)")
        st.write(top_value_counts(waste_df, waste_measure_col, top_n=20))
