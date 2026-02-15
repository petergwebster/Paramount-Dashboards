import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

tables = require_tables()

# -------------------------
# Helpers
# -------------------------
def _to_num(series_in):
    if series_in is None:
        return pd.Series([], dtype="float64")
    series_as_str = series_in.astype(str)
    series_as_str = series_as_str.str.replace(",", "", regex=False)
    series_as_str = series_as_str.str.replace("\u00a0", " ", regex=False)
    series_as_str = series_as_str.str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
    series_as_str = series_as_str.str.strip()
    series_as_str = series_as_str.replace({"": None, "None": None, "": None, "": None})
    return pd.to_numeric(series_as_str, errors="coerce")

def _make_unique_columns(cols):
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

def _promote_header_row(df_in, header_row_idx):
    if df_in is None or len(df_in) == 0:
        return None
    header_row_idx = int(header_row_idx)
    header_row_idx = max(0, min(header_row_idx, len(df_in) - 1))
    df2 = df_in.copy()
    header_vals = df2.iloc[header_row_idx].astype(str).tolist()
    df2.columns = [str(c).strip() for c in header_vals]
    df2 = df2.iloc[header_row_idx + 1 :].reset_index(drop=True)
    df2.columns = _make_unique_columns(df2.columns)
    return df2

def _pick_measure_col(df_in, prefer_exact=None, prefer_contains=None, exclude_contains=None):
    if df_in is None:
        return None

    if prefer_exact is None:
        prefer_exact = []
    if prefer_contains is None:
        prefer_contains = []
    if exclude_contains is None:
        exclude_contains = []

    for c in prefer_exact:
        if c in df_in.columns:
            return c

    candidates = []
    for c in df_in.columns:
        c_str = str(c)
        c_low = c_str.lower().strip()
        ok = True
        for ex in exclude_contains:
            if ex in c_low:
                ok = False
        if not ok:
            continue

        if len(prefer_contains) == 0:
            candidates.append(c)
        else:
            for tok in prefer_contains:
                if tok in c_low:
                    candidates.append(c)
                    break

    if len(candidates) == 0:
        return None

    best_col = None
    best_nn = -1
    for c in candidates:
        nn = int(_to_num(df_in[c]).notna().sum())
        if nn > best_nn:
            best_nn = nn
            best_col = c

    return best_col

def _numeric_strength(df_in, top_n=15):
    if df_in is None:
        return pd.DataFrame()
    rows = []
    for c in df_in.columns:
        rows.append({"col": c, "non_null_numeric": int(_to_num(df_in[c]).notna().sum())})
    return pd.DataFrame(rows).sort_values("non_null_numeric", ascending=False).head(top_n)

def _top_value_counts(df_in, col, top_n=20):
    if df_in is None or col is None or col not in df_in.columns:
        return None
    return df_in[col].astype(str).value_counts(dropna=False).head(top_n)

def _fmt_int(x):
    try:
        return format(int(round(float(x))), ",")
    except Exception:
        return ""

# -------------------------
# Load raw sheets
# -------------------------
color_raw, color_name = get_table(tables, "Color Yards")
wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yards Wasted")

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

# -------------------------
# Clean dataframes
# -------------------------
color_header_row_idx = 3
wip_header_row_idx = 4
waste_header_row_idx = 3

color_df = _promote_header_row(color_raw, color_header_row_idx)
wip_df = _promote_header_row(wip_raw, wip_header_row_idx)
waste_df = _promote_header_row(waste_raw, waste_header_row_idx)

color_measure_col = _pick_measure_col(
    color_df,
    prefer_exact=["Yards Produced"],
    prefer_contains=["yard"],
    exclude_contains=["ratio", "color x", "net yards"]
)

wip_measure_col = _pick_measure_col(
    wip_df,
    prefer_exact=["WIP", "WIP Yards", "Yards", "Total"],
    prefer_contains=["wip", "yard", "total"],
    exclude_contains=["ratio", "percent", "%"]
)

waste_measure_col = _pick_measure_col(
    waste_df,
    prefer_exact=["Yards Wasted", "Waste", "Yards"],
    prefer_contains=["waste", "yard"],
    exclude_contains=["ratio", "percent", "%"]
)

color_total = float(_to_num(color_df[color_measure_col]).sum()) if (color_df is not None and color_measure_col in color_df.columns) else 0.0
wip_total = float(_to_num(wip_df[wip_measure_col]).sum()) if (wip_df is not None and wip_measure_col in wip_df.columns) else 0.0
waste_total = float(_to_num(waste_df[waste_measure_col]).sum()) if (waste_df is not None and waste_measure_col in waste_df.columns) else 0.0

# -------------------------
# Dashboard
# -------------------------
with tab_dash:
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Color Yards", _fmt_int(color_total))
        st.caption(str(color_measure_col))

    with c2:
        st.metric("WIP", _fmt_int(wip_total))
        st.caption(str(wip_measure_col))

    with c3:
        st.metric("Yards Wasted", _fmt_int(waste_total))
        st.caption(str(waste_measure_col))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Color trend")
        if color_df is None:
            st.info("Missing Color Yards sheet.")
        elif "Weeks" not in color_df.columns:
            st.info("Missing `Weeks` column in Color.")
        elif color_measure_col is None or color_measure_col not in color_df.columns:
            st.info("No Color measure column found.")
        else:
            color_plot_df = color_df[["Weeks", color_measure_col]].copy()
            color_plot_df["Weeks"] = pd.to_numeric(color_plot_df["Weeks"], errors="coerce")
            color_plot_df[color_measure_col] = _to_num(color_plot_df[color_measure_col])
            color_plot_df = color_plot_df.dropna(subset=["Weeks"])
            color_plot_df = (
                color_plot_df.groupby("Weeks", as_index=False)[color_measure_col]
                .sum()
                .sort_values("Weeks")
            )
            if len(color_plot_df) == 0:
                st.info("No usable week rows after cleaning.")
            else:
                color_plot_df = color_plot_df.set_index("Weeks")
                st.line_chart(color_plot_df)

    with right:
        st.subheader("WIP by Division (top 15)")
        if wip_df is None:
            st.info("Missing WIP sheet.")
        elif "Division" not in wip_df.columns:
            st.info("Missing `Division` column in WIP.")
        elif wip_measure_col is None or wip_measure_col not in wip_df.columns:
            st.info("No WIP measure column found.")
        else:
            wip_plot_df = wip_df[["Division", wip_measure_col]].copy()
            wip_plot_df[wip_measure_col] = _to_num(wip_plot_df[wip_measure_col])
            wip_plot_df = wip_plot_df.dropna(subset=["Division"])
            wip_plot_df["Division"] = wip_plot_df["Division"].astype(str)
            wip_plot_df = (
                wip_plot_df.groupby("Division", as_index=False)[wip_measure_col]
                .sum()
                .sort_values(wip_measure_col, ascending=False)
                .head(15)
            )
            if len(wip_plot_df) == 0:
                st.info("No usable division rows after cleaning.")
            else:
                wip_plot_df = wip_plot_df.set_index("Division")
                st.bar_chart(wip_plot_df)

# -------------------------
# Detail tabs
# -------------------------
with tab_color:
    st.subheader("Color Yards")
    st.caption("Source sheet: " + str(color_name) + " | Header row: " + str(color_header_row_idx))
    st.write({"color_measure_col": color_measure_col})
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        st.dataframe(color_df.head(120), use_container_width=True)

with tab_wip:
    st.subheader("WIP")
    st.caption("Source sheet: " + str(wip_name) + " | Header row: " + str(wip_header_row_idx))
    st.write({"wip_measure_col": wip_measure_col})
    if wip_df is None:
        st.info("Missing WIP sheet.")
    else:
        st.dataframe(wip_df.head(120), use_container_width=True)

with tab_waste:
    st.subheader("Yards Wasted")
    st.caption("Source sheet: " + str(waste_name) + " | Header row: " + str(waste_header_row_idx))
    st.write({"waste_measure_col": waste_measure_col})
    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        st.dataframe(waste_df.head(120), use_container_width=True)

# -------------------------
# Debug
# -------------------------
with tab_debug:
    st.subheader("Debug")

    st.markdown("#### Header rows + measure cols")
    st.write(
        {
            "color_name": color_name,
            "color_header_row_idx": color_header_row_idx,
            "color_measure_col": color_measure_col,
            "wip_name": wip_name,
            "wip_header_row_idx": wip_header_row_idx,
            "wip_measure_col": wip_measure_col,
            "waste_name": waste_name,
            "waste_header_row_idx": waste_header_row_idx,
            "waste_measure_col": waste_measure_col,
        }
    )

    st.markdown("#### Numeric strength (top 15 columns)")
    st.markdown("Color")
    st.dataframe(_numeric_strength(color_df, top_n=15), use_container_width=True)
    st.markdown("WIP")
    st.dataframe(_numeric_strength(wip_df, top_n=15), use_container_width=True)
    st.markdown("Waste")
    st.dataframe(_numeric_strength(waste_df, top_n=15), use_container_width=True)

    st.markdown("#### Value counts (top 20) for measure cols")
    st.markdown("Color measure")
    st.write(_top_value_counts(color_df, color_measure_col, top_n=20))
    st.markdown("WIP measure")
    st.write(_top_value_counts(wip_df, wip_measure_col, top_n=20))
    st.markdown("Waste measure")
    st.write(_top_value_counts(waste_df, waste_measure_col, top_n=20))

    st.markdown("#### Raw heads (before header promotion)")
    if color_raw is not None:
        st.markdown("Color raw head")
        st.dataframe(color_raw.head(12), use_container_width=True)
    if wip_raw is not None:
        st.markdown("WIP raw head")
        st.dataframe(wip_raw.head(12), use_container_width=True)
    if waste_raw is not None:
        st.markdown("Waste raw head")
        st.dataframe(waste_raw.head(12), use_container_width=True)
