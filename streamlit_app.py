import os
import pandas as pd
import streamlit as st

st.subheader("Dashboard Builder")

uploaded_file = st.file_uploader("Upload Excel (optional)", type=["xlsx", "xls"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.caption("Using uploaded file for this session only.")
else:
    df = pd.read_excel("data/current.xlsx")
    st.caption("Loading dataset from data/current.xlsx")
import datetime

file_mtime = os.path.getmtime("data/current.xlsx")
st.caption(
    "Published data last updated: "
    + datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")

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

