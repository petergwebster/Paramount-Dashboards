import pandas as pd
import streamlit as st
from data_loader import load_df, show_published_timestamp

st.set_page_config(page_title="Explore", layout="wide")

st.title("Explore")
show_published_timestamp()

df = load_df()

with st.expander("Preview", expanded=False):
    st.dataframe(df.head(25), use_container_width=True)

st.divider()

# --- Filters ---
st.subheader("Filters")

filter_cols = st.multiselect("Choose columns to filter", options=list(df.columns))

df_filtered = df.copy()

for col_name in filter_cols:
    col_vals = df_filtered[col_name]

    # Numeric filter
    as_num = pd.to_numeric(col_vals, errors="coerce")
    if as_num.notna().any() and (col_vals.dtype != "object"):
        min_val = float(as_num.min())
        max_val = float(as_num.max())
        selected_range = st.slider(
            "Range for " + str(col_name),
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
        )
        df_filtered = df_filtered[as_num.between(selected_range[0], selected_range[1], inclusive="both")]
    else:
        # Categorical filter
        uniq_vals = col_vals.dropna().astype(str).unique().tolist()
        uniq_vals = sorted(uniq_vals) if len(uniq_vals) <= 5000 else uniq_vals
        chosen_vals = st.multiselect("Values for " + str(col_name), options=uniq_vals)
        if len(chosen_vals) > 0:
            df_filtered = df_filtered[col_name].astype(str).isin(chosen_vals) and df_filtered

# Fix the categorical filtering logic (Streamlit needs boolean mask; keep it simple)
# Re-apply categorical filters properly
df_filtered = df.copy()
for col_name in filter_cols:
    col_vals = df_filtered[col_name]
    as_num = pd.to_numeric(col_vals, errors="coerce")

    if as_num.notna().any() and (col_vals.dtype != "object"):
        min_val = float(as_num.min())
        max_val = float(as_num.max())
        selected_range = st.session_state.get("Range for " + str(col_name))
        if selected_range is None:
            selected_range = (min_val, max_val)
        df_filtered = df_filtered[pd.to_numeric(df_filtered[col_name], errors="coerce").between(selected_range[0], selected_range[1], inclusive="both")]
    else:
        chosen_vals = st.session_state.get("Values for " + str(col_name))
        if chosen_vals is not None and len(chosen_vals) > 0:
            df_filtered = df_filtered[df_filtered[col_name].astype(str).isin(chosen_vals)]

st.write("Rows after filtering: " + str(len(df_filtered)))
st.dataframe(df_filtered.head(200), use_container_width=True)

st.divider()

# --- Groupby / Pivot ---
st.subheader("Group and summarize")

group_cols = st.multiselect("Group by", options=list(df.columns))
metric_col = st.selectbox("Metric column (optional)", options=["(count rows)"] + list(df.columns))

agg_method = st.selectbox("Aggregation", options=["sum", "mean", "min", "max", "count"])

if len(group_cols) == 0:
    st.info("Pick at least one Group by column to generate a summary table.")
else:
    if metric_col == "(count rows)":
        summary_series = df_filtered.groupby(group_cols, dropna=False).size()
        summary_df = summary_series.reset_index(name="rows")
    else:
        metric_vals = pd.to_numeric(df_filtered[metric_col], errors="coerce")
        df_tmp = df_filtered.copy()
        df_tmp[metric_col] = metric_vals

        if agg_method == "sum":
            summary_df = df_tmp.groupby(group_cols, dropna=False)[metric_col].sum().reset_index()
        elif agg_method == "mean":
            summary_df = df_tmp.groupby(group_cols, dropna=False)[metric_col].mean().reset_index()
        elif agg_method == "min":
            summary_df = df_tmp.groupby(group_cols, dropna=False)[metric_col].min().reset_index()
        elif agg_method == "max":
            summary_df = df_tmp.groupby(group_cols, dropna=False)[metric_col].max().reset_index()
        else:
            summary_df = df_tmp.groupby(group_cols, dropna=False)[metric_col].count().reset_index()

    st.dataframe(summary_df.head(500), use_container_width=True)

    st.subheader("Quick chart")
    if len(group_cols) == 1:
        x_col = group_cols[0]
        y_col = summary_df.columns[-1]
        chart_df = summary_df.sort_values(y_col, ascending=False).head(50).set_index(x_col)
        st.bar_chart(chart_df[y_col])
    else:
        st.caption("Charts are only auto-generated for 1-column group by (keeps it readable).")
