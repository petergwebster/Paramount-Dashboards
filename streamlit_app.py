import os
import pandas as pd
import streamlit as st

candidate_paths = [
    "data/current.xlsx",
    "data/WIP Current Data.xlsx",
    "WIP Current Data.xlsx",
]

found_path = None
for p in candidate_paths:
    if os.path.exists(p):
        found_path = p
        break

if found_path is None:
    st.error("Could not find an Excel file. Looked for: " + ", ".join(candidate_paths))
    st.write("Repo root files:", os.listdir("."))
    if os.path.exists("data"):
        st.write("data/ files:", os.listdir("data"))
    st.stop()

st.caption("Loading dataset from " + found_path)
df = pd.read_excel(found_path)

df = pd.read_excel(uploaded_file)
st.subheader("Dashboard Builder")

filter_cols = st.multiselect("Filter columns (optional)", options=list(df.columns))
df_filtered = df.copy()

for filter_col in filter_cols:
    vals = df_filtered[filter_col].astype(str).fillna("(blank)")
    unique_vals = sorted(vals.unique().tolist())
    chosen_vals = st.multiselect("Filter " + str(filter_col), options=unique_vals)
    if len(chosen_vals) > 0:
        df_filtered = df_filtered[vals.isin(chosen_vals)]

st.caption("Rows after filters: " + str(len(df_filtered)))

st.divider()

group_col = st.selectbox(
    "Group by",
    options=list(df.columns),
    index=list(df.columns).index("PRODUCT_TYPE") if "PRODUCT_TYPE" in df.columns else 0
)

agg_mode = st.selectbox("Metric", options=["Count rows", "Count unique", "Sum", "Average"])
value_col = None
if agg_mode in ["Count unique", "Sum", "Average"]:
    value_col = st.selectbox("Value column", options=list(df.columns))

top_n = st.slider("Show top N groups", min_value=5, max_value=50, value=20, step=5)

if agg_mode == "Count rows":
    summary_series = df_filtered.groupby(group_col, dropna=False).size()
    summary_df = summary_series.to_frame("Value").reset_index()
elif agg_mode == "Count unique":
    summary_series = df_filtered.groupby(group_col, dropna=False)[value_col].nunique()
    summary_df = summary_series.to_frame("Value").reset_index()
elif agg_mode == "Sum":
    summary_series = pd.to_numeric(df_filtered[value_col], errors="coerce").groupby(df_filtered[group_col]).sum()
    summary_df = summary_series.to_frame("Value").reset_index()
else:
    summary_series = pd.to_numeric(df_filtered[value_col], errors="coerce").groupby(df_filtered[group_col]).mean()
    summary_df = summary_series.to_frame("Value").reset_index()

summary_df = summary_df.sort_values("Value", ascending=False).head(top_n)

st.subheader("Summary table")
st.dataframe(summary_df, use_container_width=True)

st.subheader("Chart")
st.bar_chart(summary_df.set_index(group_col)["Value"])
st.subheader("Preview")
st.dataframe(df.head(50), use_container_width=True)

st.subheader("Columns")
st.write(list(df.columns))
st.divider()

