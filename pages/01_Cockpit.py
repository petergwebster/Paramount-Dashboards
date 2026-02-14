import pandas as pd
import streamlit as st
from data_loader import load_df, show_published_timestamp

st.set_page_config(page_title="Cockpit", layout="wide")

st.title("Cockpit")
show_published_timestamp()

df = load_df()

# Find a reasonable date column (optional)
date_candidates = ["DATE", "Date", "date", "REPORT_DATE", "Report Date", "WORK_DATE", "Work Date"]
date_col = None
for c in date_candidates:
    if c in df.columns:
        date_col = c
        break

# Find numeric columns for placeholder KPI and trend
numeric_cols = []
for c in df.columns:
    s = pd.to_numeric(df[c], errors="coerce")
    if s.notna().any():
        numeric_cols.append(c)

primary_value_col = numeric_cols[0] if len(numeric_cols) > 0 else None

# KPIs
col_a, col_b, col_c = st.columns(3)
col_a.metric("Rows", str(len(df)))
col_b.metric("Columns", str(len(df.columns)))

if primary_value_col is not None:
    total_val = pd.to_numeric(df[primary_value_col], errors="coerce").sum()
    col_c.metric("Total " + str(primary_value_col), str(round(float(total_val), 2)))
else:
    col_c.metric("Total (numeric)", "No numeric columns found")

st.divider()

# Trend
st.subheader("Trend")

if date_col is None:
    st.write("No obvious date column found yet. If you add one (like DATE), this will become a trend chart.")
else:
    df_trend = df.copy()
    df_trend[date_col] = pd.to_datetime(df_trend[date_col], errors="coerce")
    df_trend = df_trend.dropna(subset=[date_col]).sort_values(date_col)

    if primary_value_col is None:
        trend_series = df_trend.groupby(pd.Grouper(key=date_col, freq="D")).size()
        trend_df = trend_series.to_frame("Rows").reset_index()
        st.line_chart(trend_df.set_index(date_col)["Rows"])
    else:
        df_trend[primary_value_col] = pd.to_numeric(df_trend[primary_value_col], errors="coerce")
        trend_series = df_trend.groupby(pd.Grouper(key=date_col, freq="D"))[primary_value_col].sum()
        trend_df = trend_series.to_frame("Total").reset_index()
        st.line_chart(trend_df.set_index(date_col)["Total"])

st.divider()

# Top groups (defaults to PRODUCT_TYPE if present)
st.subheader("Top groups")

group_col = "PRODUCT_TYPE" if "PRODUCT_TYPE" in df.columns else None
if group_col is None:
    for c in df.columns:
        if c != date_col and df[c].dtype == "object":
            group_col = c
            break

if group_col is None:
    st.write("No good grouping column found to show a top-groups chart.")
else:
    top_n = st.slider("Top N", min_value=5, max_value=50, value=10, step=5)

    if primary_value_col is None:
        grp_series = df.groupby(group_col, dropna=False).size().sort_values(ascending=False).head(top_n)
        grp_df = grp_series.to_frame("Rows").reset_index()
        st.bar_chart(grp_df.set_index(group_col)["Rows"])
        st.dataframe(grp_df, use_container_width=True)
    else:
        df_grp = df.copy()
        df_grp[primary_value_col] = pd.to_numeric(df_grp[primary_value_col], errors="coerce")
        grp_series = df_grp.groupby(group_col, dropna=False)[primary_value_col].sum().sort_values(ascending=False).head(top_n)
        grp_df = grp_series.to_frame("Total").reset_index()
        st.bar_chart(grp_df.set_index(group_col)["Total"])
        st.dataframe(grp_df, use_container_width=True)
