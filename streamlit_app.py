import streamlit as st
from data_loader import load_df, show_published_timestamp

st.set_page_config(page_title="Paramount KPI Portal", layout="wide")

st.title("Paramount KPI Portal")
show_published_timestamp()

df = load_df()

st.write("Use the left sidebar to switch between pages as we add them.")
st.divider()

st.subheader("Quick preview")
st.dataframe(df.head(25), use_container_width=True)

st.subheader("Columns")
st.write(list(df.columns))
