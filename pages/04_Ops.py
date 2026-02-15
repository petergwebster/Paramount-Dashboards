import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

sns.set_theme(style="whitegrid")

tables = require_tables()

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
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

def _guess_header_row(df_in, prefer_tokens=None, max_scan_rows=60):
    if df_in is None or len(df_in) == 0:
        return 0
    if prefer_tokens is None:
        prefer_tokens = []

    scan_rows = min(max_scan_rows, len(df_in))
    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)
        for tok in prefer_tokens:
            if tok in joined:
                return i

    for i in range(scan_rows):
        row_vals = df_in.iloc[i].astype(str).str.lower().tolist()
        joined = " ".join(row_vals)
        if "yards" in joined or "yard" in joined:
            return i

    return 0

def _numeric_strength(df_in, top_n=15):
    if df_in is None:
        return pd.DataFrame()
    strength_rows = []
    for c in df_in.columns:
        strength_rows.append({"col": c, "non_null_numeric": int(_to_num(df_in[c]).notna().sum())})
    return pd.DataFrame(strength_rows).sort_values("non_null_numeric", ascending=False).head(top_n)

def _top_value_counts(df_in, col_name, top_n=25):
    if df_in is None or col_name is None or col_name not in df_in.columns:
        return None
    return df_in[col_name].astype(str).value_counts(dropna=False).head(top_n)

def _pick_color_measure_col(df_in):
    if df_in is None:
        return None
    if "Yards Produced" in df_in.columns:
        return "Yards Produced"

    candidates = []
    for c in df_in.columns:
        c_low = str(c).lower().strip()
        if "yard" in c_low and "ratio" not in c_low and "color x" not in c_low and "net yards" not in c_low:
            candidates.append(c)

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

def _pick_wip_measure_col(df_in):
    if df_in is None:
        return None
    if "Total Yards Held to Invoice" in df_in.columns:
        return "Total Yards Held to Invoice"

    candidates = []
    for c in df_in.columns:
        c_low = str(c).lower().strip()
        if "held" in c_low or ("invoice" in c_low and "yard" in c_low):
            candidates.append(c)

    if len(candidates) == 0:
        for c in df_in.columns:
            c_low = str(c).lower().strip()
            if "yard" in c_low:
                candidates.append(c)

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

def _pick_waste_mode(df_in):
    if df_in is None:
        return {"mode": "none", "measure_col": None, "sum_cols": []}

    preferred = ["Yards Wasted", "Waste", "Wasted Yards", "Total Waste", "Total Wasted"]
    for c in df_in.columns:
        c_str = str(c).strip()
        if c_str in preferred:
            return {"mode": "single_col", "measure_col": c_str, "sum_cols": []}

    for c in df_in.columns:
        c_low = str(c).lower().strip()
        if "waste" in c_low and "yard" in c_low:
            return {"mode": "single_col", "measure_col": c, "sum_cols": []}

    sum_cols = []
    for c in df_in.columns:
        c_low = str(c).lower().strip()
        if c_low in ["division", "product type grouped", "values", "grand total", "fabric", "weeks", "445 month label", "445 year"]:
            continue
        if c_low == "" or c_low == "unnamed":
            continue
        nn = int(_to_num(df_in[c]).notna().sum())
        if nn > 0:
            sum_cols.append(c)

    if len(sum_cols) > 0:
        return {"mode": "sum_numeric_cols", "measure_col": None, "sum_cols": sum_cols}

    return {"mode": "none", "measure_col": None, "sum_cols": []}

def _fmt_int(x):
    try:
        return format(int(round(float(x))), ",")
    except Exception:
        return ""

# ------------------------------------------------------------
# Load raw sheets
# ------------------------------------------------------------
color_raw, color_name = get_table(tables, "Color Yards")
wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yards Wasted")

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

# ------------------------------------------------------------
# Promote headers and select measure columns
# ------------------------------------------------------------
color_header_row_idx = _guess_header_row(color_raw, prefer_tokens=["445 year", "weeks", "yards produced"])
wip_header_row_idx = _guess_header_row(wip_raw, prefer_tokens=["division", "yards written", "held to invoice"])
waste_header_row_idx = _guess_header_row(waste_raw, prefer_tokens=["values", "grand total", "yards"])

color_df = _promote_header_row(color_raw, color_header_row_idx)
wip_df = _promote_header_row(wip_raw, wip_header_row_idx)
waste_df = _promote_header_row(waste_raw, waste_header_row_idx)

color_measure_col = _pick_color_measure_col(color_df)
wip_measure_col = _pick_wip_measure_col(wip_df)

waste_mode_obj = _pick_waste_mode(waste_df)
waste_mode = waste_mode_obj["mode"]
waste_measure_col = waste_mode_obj["measure_col"]
waste_sum_cols = waste_mode_obj["sum_cols"]

# ------------------------------------------------------------
# KPI totals
# ------------------------------------------------------------
color_total = 0.0
if color_df is not None and color_measure_col is not None and color_measure_col in color_df.columns:
    color_total = float(_to_num(color_df[color_measure_col]).sum(skipna=True))

wip_total = 0.0
if wip_df is not None and wip_measure_col is not None and wip_measure_col in wip_df.columns:
    wip_total = float(_to_num(wip_df[wip_measure_col]).sum(skipna=True))

waste_total = 0.0
if waste_df is not None:
    if waste_mode == "single_col" and waste_measure_col is not None and waste_measure_col in waste_df.columns:
        waste_total = float(_to_num(waste_df[waste_measure_col]).sum(skipna=True))
    elif waste_mode == "sum_numeric_cols" and len(waste_sum_cols) > 0:
        tmp_sum = 0.0
        for c in waste_sum_cols:
            tmp_sum = tmp_sum + float(_to_num(waste_df[c]).sum(skipna=True))
        waste_total = tmp_sum

# ------------------------------------------------------------
# Dashboard tab (KPIs + charts)
# ------------------------------------------------------------
with tab_dash:
    st.subheader("Ops snapshot")

    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards", _fmt_int(color_total))
    c2.metric("WIP yards", _fmt_int(wip_total))
    c3.metric("Yards wasted", _fmt_int(waste_total))

    st.divider()

    st.markdown("#### Color trend")
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    elif "Weeks" not in color_df.columns:
        st.info("Could not chart Color: missing `Weeks` column.")
    elif color_measure_col is None or color_measure_col not in color_df.columns:
        st.info("Could not chart Color: no valid measure column found.")
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
            st.info("No usable rows to chart for Color after cleaning.")
        else:
            plt.figure(figsize=(10, 4))
            sns.lineplot(data=color_plot_df, x="Weeks", y=color_measure_col, marker="o")
            plt.title("Color Yards: " + str(color_measure_col) + " by Week")
            plt.tight_layout()
            st.pyplot(plt.gcf())
            plt.close()

    st.markdown("#### WIP by division")
    if wip_df is None:
        st.info("Missing WIP sheet.")
    elif "Division" not in wip_df.columns:
        st.info("Could not chart WIP: missing `Division` column.")
    elif wip_measure_col is None or wip_measure_col not in wip_df.columns:
        st.info("Could not chart WIP: no valid measure column found.")
    else:
        wip_plot_df = wip_df[["Division", wip_measure_col]].copy()
        wip_plot_df[wip_measure_col] = _to_num(wip_plot_df[wip_measure_col])
        wip_plot_df = wip_plot_df.dropna(subset=["Division"])
        wip_plot_df = (
            wip_plot_df.groupby("Division", as_index=False)[wip_measure_col]
            .sum()
            .sort_values(wip_measure_col, ascending=False)
            .head(15)
        )

        if len(wip_plot_df) == 0:
            st.info("No usable rows to chart for WIP after cleaning.")
        else:
            plt.figure(figsize=(10, 5))
            sns.barplot(data=wip_plot_df, x=wip_measure_col, y="Division")
            plt.title("WIP: " + str(wip_measure_col) + " by Division (top 15)")
            plt.tight_layout()
            st.pyplot(plt.gcf())
            plt.close()

    st.caption("Waste charts are next (doing Waste last).")

# ------------------------------------------------------------
# Detail tabs
# ------------------------------------------------------------
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

    waste_debug_obj = {"mode": waste_mode, "measure_col": waste_measure_col, "sum_cols_count": len(waste_sum_cols)}
    if len(waste_sum_cols) > 0:
        waste_debug_obj["sum_cols_preview"] = waste_sum_cols[:25]
    st.write(waste_debug_obj)

    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        st.dataframe(waste_df.head(120), use_container_width=True)

# ------------------------------------------------------------
# Debug tab
# ------------------------------------------------------------
with tab_debug:
    st.subheader("Chosen columns / header rows")
    debug_obj = {
        "color_sheet": color_name,
        "color_header_row_idx": color_header_row_idx,
        "color_measure_col": color_measure_col,
        "color_total": color_total,
        "wip_sheet": wip_name,
        "wip_header_row_idx": wip_header_row_idx,
        "wip_measure_col": wip_measure_col,
        "wip_total": wip_total,
        "waste_sheet": waste_name,
        "waste_header_row_idx": waste_header_row_idx,
        "waste_mode": waste_mode,
        "waste_measure_col": waste_measure_col,
        "waste_sum_cols_preview": waste_sum_cols[:30],
        "waste_total": waste_total,
    }
    st.write(debug_obj)

    st.markdown("#### Numeric strength (top 15)")
    st.markdown("Color")
    st.dataframe(_numeric_strength(color_df, top_n=15), use_container_width=True)
    st.markdown("WIP")
    st.dataframe(_numeric_strength(wip_df, top_n=15), use_container_width=True)
    st.markdown("Waste")
    st.dataframe(_numeric_strength(waste_df, top_n=15), use_container_width=True)

    st.markdown("#### Measure column value counts (top 25)")
    st.markdown("Color")
    st.write(_top_value_counts(color_df, color_measure_col, top_n=25))
    st.markdown("WIP")
    st.write(_top_value_counts(wip_df, wip_measure_col, top_n=25))
    st.markdown("Waste")
    if waste_mode == "single_col":
        st.write(_top_value_counts(waste_df, waste_measure_col, top_n=25))
    else:
        st.write({"waste_mode": waste_mode, "waste_sum_cols_preview": waste_sum_cols[:40]})

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
