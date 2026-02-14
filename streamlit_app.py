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
