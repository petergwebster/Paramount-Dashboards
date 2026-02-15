import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

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

def _pick_color_measure_col(color_df):
    if color_df is None:
        return None

    if "Yards Produced" in color_df.columns:
        return "Yards Produced"

    candidates = []
    for c in color_df.columns:
        c_low = str(c).lower().strip()
        if "yard" in c_low and "color x" not in c_low and "ratio" not in c_low:
            candidates.append(c)

    if len(candidates) == 0:
        return None

    best_col = None
    best_nn = -1
    for c in candidates:
        nn = int(_to_num(color_df[c]).notna().sum())
        if nn > best_nn:
            best_nn = nn
            best_col = c

    return best_col

def _fmt_int(x):
    try:
        return format(int(round(float(x))), ",")
    except Exception:
        return ""

# ---- COLOR YARDS: clean + lock + visualize ----
color_header_row_idx = 3
color_df = None
color_measure_col = None
color_total = 0.0

if color_raw is not None:
    color_df = _promote_header_row(color_raw, color_header_row_idx)
    color_measure_col = _pick_color_measure_col(color_df)

    if color_measure_col is not None and color_measure_col in color_df.columns:
        color_total = float(_to_num(color_df[color_measure_col]).sum(skipna=True))

tab_dash, tab_color, tab_wip, tab_waste, tab_debug = st.tabs(["Dashboard", "Color Yards", "WIP", "Yards Wasted", "Debug"])

with tab_dash:
    st.subheader("Ops snapshot")
    st.metric("Color yards (sum)", _fmt_int(color_total))
    st.caption("Color measure column locked to: " + str(color_measure_col))

    st.markdown("#### Color trend")
    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        if "Weeks" in color_df.columns and color_measure_col is not None and color_measure_col in color_df.columns:
            color_plot_df = color_df[["Weeks", color_measure_col]].copy()
            color_plot_df["Weeks"] = pd.to_numeric(color_plot_df["Weeks"], errors="coerce")
            color_plot_df[color_measure_col] = _to_num(color_plot_df[color_measure_col])
            color_plot_df = color_plot_df.dropna(subset=["Weeks"])
            color_plot_df = (
                color_plot_df.groupby("Weeks", as_index=False)[color_measure_col]
                .sum()
                .sort_values("Weeks")
            )

            plt.figure(figsize=(10, 4))
            sns.lineplot(data=color_plot_df, x="Weeks", y=color_measure_col, marker="o")
            plt.title("Color Yards: " + str(color_measure_col) + " by Week")
            plt.tight_layout()
            st.pyplot(plt.gcf())
            plt.close()
        else:
            st.info("Could not chart Color trend. Need columns `Weeks` and a yards measure column.")

with tab_color:
    st.subheader("Color Yards")
    st.caption("Header promoted from row: " + str(color_header_row_idx))
    st.write({"color_measure_col": color_measure_col})

    if color_df is None:
        st.info("Missing Color Yards sheet.")
    else:
        st.dataframe(color_df.head(80), use_container_width=True)

with tab_debug:
    st.subheader("Color debug")
    st.write(
        {
            "color_header_row_idx": color_header_row_idx,
            "color_measure_col": color_measure_col,
            "color_total": color_total,
        }
    )

    if color_raw is not None:
        st.markdown("#### Raw head (before header promotion)")
        st.dataframe(color_raw.head(12), use_container_width=True)

    if color_df is not None:
        st.markdown("#### Clean head (after header promotion + dedupe)")
        st.dataframe(color_df.head(60), use_container_width=True)

        st.markdown("#### Numeric strength (top 15)")
        strength_rows = []
        for c in color_df.columns:
            strength_rows.append(
                {
                    "col": c,
                    "non_null_numeric": int(_to_num(color_df[c]).notna().sum()),
                }
            )
        strength_df = pd.DataFrame(strength_rows).sort_values("non_null_numeric", ascending=False).head(15)
        st.dataframe(strength_df, use_container_width=True)
