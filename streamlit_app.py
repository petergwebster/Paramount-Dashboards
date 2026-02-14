import streamlit as st
import pandas as pd

st.set_page_config(page_title="Paramount Dashboard", layout="wide")
st.title("Paramount Dashboard")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])
if uploaded_file is None:
    st.info("Upload an Excel file to begin.")
    st.stop()

df = pd.read_excel(uploaded_file)

st.subheader("Preview")
st.dataframe(df.head(50), use_container_width=True)

st.subheader("Columns")
st.write(list(df.columns))
st.divider()
st.header("Quick Summary")

group_col = st.selectbox(
    "Group by",
    options=list(df.columns),
    index=list(df.columns).index("PRODUCT_TYPE") if "PRODUCT_TYPE" in df.columns else 0
)

summary_df = (
    df.groupby(group_col, dropna=False)
      .size()
      .reset_index(name="Count")
      .sort_values("Count", ascending=False)
)

st.subheader("Counts")
st.dataframe(summary_df, use_container_width=True)

st.subheader("Chart")
st.bar_chart(summary_df.set_index(group_col)["Count"])
