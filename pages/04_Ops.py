import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from app_tables import require_tables, get_table

st.set_page_config(page_title="Ops", layout="wide")
st.title("Ops")

sns.set_theme(style="whitegrid")

tables = require_tables()

# -------------------------
# Helpers
# -------------------------
def _to_num(series_in):
    series_as_str = series_in.astype(str)
    series_as_str = series_as_str.str.replace(",", "", regex=False)
    series_as_str = series_as_str.str.replace("\u00a0", " ", regex=False)
    series_as_str = series_as_str.str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
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
    df2 = df_in.copy()
    header_vals = df2.iloc[header_row_idx].astype(str).tolist()
    df2.columns = [str(c).strip() for c in header_vals]
    df2 = df2.iloc[header_row_idx + 1 :].reset_index(drop=True)
    df2.columns = _make_unique_columns(df2.columns)
    return df2

def _guess_header_row(df_in, prefer_tokens=None, max_scan_rows=50):
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
        if "yards" in joined:
            return i

    return 0

def _fmt_int(x):
    try:
        return format(int(round(float(x))), ",")
    except Exception:
        return ""

def _numeric_strength(df_in, top_n=15):
    if df_in is None:
        return pd.DataFrame()

    rows = []
    for c in df_in.columns:
        nn = int(_to_num(df_in[c]).notna().sum())
        rows.append({"col": c, "non_null_numeric": nn})
    return pd.DataFrame(rows).sort_values("non_null_numeric", ascending=False).head(top_n)

def _top_value_counts(df_in, col_name, top_n=20):
    if df_in is None or col_name is None or col_name not in df_in.columns:
        return None
    return (
        df_in[col_name]
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
        .value_counts(dropna=False)
        .head(top_n)
    )

# -------------------------
# Load raw sheets
# -------------------------
color_raw, color_name = get_table(tables, "Color Yards")
wip_raw, wip_name = get_table(tables, "WIP")
waste_raw, waste_name = get_table(tables, "Yards Wasted")

# -------------------------
# Clean Color
# -------------------------
color_header_row_idx = _guess_header_row(color_raw, prefer_tokens=["445 year", "weeks", "yards produced"])
if color_header_row_idx is None:
    color_header_row_idx = 3

color_df = None
if color_raw is not None:
    color_df = _promote_header_row(color_raw, color_header_row_idx)

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

color_measure_col = _pick_color_measure_col(color_df)
color_total = 0.0
if color_df is not None and color_measure_col is not None and color_measure_col in color_df.columns:
    color_total = float(_to_num(color_df[color_measure_col]).sum(skipna=True))

# -------------------------
# Clean WIP
# -------------------------
wip_header_row_idx = _guess_header_row(wip_raw, prefer_tokens=["total yards held to invoice", "division", "yard order status"])
if wip_header_row_idx is None:
    wip_header_row_idx = 4

wip_df = None
if wip_raw is not None:
    wip_df = _promote_header_row(wip_raw, wip_header_row_idx)

def _pick_wip_measure_col(df_in):
    if df_in is None:
        return None
    if "Total Yards Held to Invoice" in df_in.columns:
        return "Total Yards Held to Invoice"
    if "Total Yards Held to Invoice__1" in df_in.columns:
        return "Total Yards Held to Invoice__1"

    candidates = []
    for c in df_in.columns:
        c_low = str(c).lower().strip()
        if "held" in c_low and "invoice" in c_low and "yard" in c_low:
            candidates.append(c)

    if len(candidates) == 0:
        for c in df_in.columns:
            c_low = str(c).lower().strip()
            if "yards" in c_low and ("held" in c_low or "wip" in c_low):
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

wip_measure_col = _pick_wip_measure_col(wip_df)
wip_total = 0.0
if wip_df is not None and wip_measure_col is not None and wip_measure_col in wip_df.columns:
    wip_total = float(_to_num(wip_df[wip_measure_col]).sum(skipna=True))

# -------------------------
# Clean Waste (do last; we will chart optionally)
# Strategy
# Use Grand Total if present; otherwise sum across month-ish numeric columns
# -------------------------
waste_header_row_idx = _guess_header_row(waste_raw, prefer_tokens=["grand total", "yards produced", "fabric", "values"])
if waste_header_row_idx is None:
    waste_header_row_idx = 3

waste_df = None
if waste_raw is not None:
    waste_df = _promote_header_row(waste_raw, waste_header_row_idx)

def _pick_waste_mode_and_cols(df_in):
    if df_in is None:
        return {"mode": "none", "measure_col": None, "sum_cols": []}

    if "Grand Total" in df_in.columns:
        return {"mode": "grand_total", "measure_col": "Grand Total", "sum_cols": []}

    exclude_tokens = ["fabric", "screen", "print", "yards produced", "produced", "values", "product", "division"]
    sum_cols = []
    for c in df_in.columns:
        c_low = str(c).lower().strip()
        skip = False
        for tok in exclude_tokens:
            if tok in c_low:
                skip = True
                break
        if skip:
            continue

        nn = int(_to_num(df_in[c]).notna().sum())
        if nn > 0:
            sum_cols.append(c)

    if len(sum_cols) == 0:
        return {"mode": "none", "measure_col": None, "sum_cols": []}

    return {"mode": "sum_cols", "measure_col": None, "sum_cols": sum_cols}

waste_mode_obj = _pick_waste_mode_and_cols(waste_df)
waste_total = 0.0
waste_measure_col = None
waste_sum_cols = []

if waste_mode_obj["mode"] == "grand_total":
    waste_measure_col = waste_mode_obj["measure_col"]
    waste_total = float(_to_num(waste_df[waste_measure_col]).sum(skipna=True))
elif waste_mode_obj["mode"] == "sum_cols":
    waste_sum_cols = waste_mode_obj["sum_cols"]
    waste_total = float(_to_num(waste_df[waste_sum_cols].stack()).sum(skipna=True))

# -------------------------
# Tabs
# -------------------------
tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(
    ["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"]
)

# -------------------------
# Dashboard (KPIs + charts)
# -------------------------
with tab_dash:
    st.subheader("Ops snapshot")

    c1, c2, c3 = st.columns(3)
    c1.metric("Color yards (sum)", _fmt_int(color_total))
    c2.metric("WIP yards (sum)", _fmt_int(wip_total))
    c3.metric("Yards wasted (sum)", _fmt_int(waste_total))

    st.caption("Charts: Color + WIP now. Waste chart later if you want it.")

    st.markdown("#### Color trend")
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    elif "Weeks" not in color_df.columns:
        st.info("Could not chart Color (missing `Weeks`).")
    elif color_measure_col is None or color_measure_col not in color_df.columns:
        st.info("Could not chart Color (no valid measure column).")
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
            st.info("No usable rows to chart for Color.")
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
        st.info("Could not chart WIP (missing `Division`).")
    elif wip_measure_col is None or wip_measure_col not in wip_df.columns:
        st.info("Could not chart WIP (no valid measure column).")
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
            st.info("No usable rows to chart for WIP.")
        else:
            plt.figure(figsize=(10, 5))
            sns.barplot(data=wip_plot_df, x=wip_measure_col, y="Division")
            plt.title("WIP: " + str(wip_measure_col) + " by Division (top 15)")
            plt.tight_layout()
            st.pyplot(plt.gcf())
            plt.close()

# -------------------------
# Color tab
# -------------------------
with tab_color:
    st.subheader("Color Yards")
    st.caption("Source sheet: " + str(color_name) + " | Header promoted from row: " + str(color_header_row_idx))
    st.write({"color_measure_col": color_measure_col})
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        st.dataframe(color_df.head(80), use_container_width=True)

# -------------------------
# WIP tab
# -------------------------
with tab_wip:
    st.subheader("WIP")
    st.caption("Source sheet: " + str(wip_name) + " | Header promoted from row: " + str(wip_header_row_idx))
    st.write({"wip_measure_col": wip_measure_col})
    if wip_df is None:
        st.info("Missing WIP sheet.")
    else:
        st.dataframe(wip_df.head(80), use_container_width=True)

# -------------------------
# Waste tab (table only for now)
# -------------------------
with tab_waste:
    st.subheader("Yards Wasted")
    st.caption("Source sheet: " + str(waste_name) + " | Header promoted from row: " + str(waste_header_row_idx))
    st.write({"waste_mode": waste_mode_obj["mode"], "waste_measure_col": waste_measure_col, "waste_sum_cols_count": len(waste_sum_cols)})
    if waste_df is None:
        st.info("Missing Yards Wasted sheet.")
    else:
        st.dataframe(waste_df.head(80), use_container_width=True)

# -------------------------
# Debug tab
# -------------------------
with tab_debug:
    st.subheader("Chosen columns / header rows")
    st.write(
        {
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
            "waste_mode": waste_mode_obj["mode"],
            "waste_measure_col": waste_measure_col,
            "waste_sum_cols": waste_sum_cols[:30],
            "waste_total": waste_total,
        }
    )

    st.markdown("#### Numeric strength (Color)")
    st.dataframe(_numeric_strength(color_df, top_n=15), use_container_width=True)

    st.markdown("#### Numeric strength (WIP)")
    st.dataframe(_numeric_strength(wip_df, top_n=15), use_container_width=True)

    st.markdown("#### Numeric strength (Waste)")
    st.dataframe(_numeric_strength(waste_df, top_n=15), use_container_width=True)

    st.markdown("#### Measure column value counts (Color)")
    st.write(_top_value_counts(color_df, color_measure_col, top_n=20))

    st.markdown("#### Measure column value counts (WIP)")
    st.write(_top_value_counts(wip_df, wip_measure_col, top_n=20))

    st.markdown("#### Waste column preview")
    if waste_df is None:
        st.write(None)
    elif waste_measure_col is not None and waste_measure_col in waste_df.columns:
        st.write(_top_value_counts(waste_df, waste_measure_col, top_n=20))
    else:
        if len(waste_sum_cols) > 0:
            st.write(waste_sum_cols[:50])
        else:
            st.write(None)

    st.markdown("#### Raw heads (before header promotion)")
    if color_raw is not None:
        st.markdown("Color raw head")
        st.dataframe(color_raw.head(10), use_container_width=True)
    if wip_raw is not None:
        st.markdown("WIP raw head")
        st.dataframe(wip_raw.head(10), use_container_width=True)
    if waste_raw is not None:
        st.markdown("Waste raw head")
        st.dataframe(waste_raw.head(10), use_container_width=True)
