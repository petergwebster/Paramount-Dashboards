import streamlit as st

from data_sync import ensure_latest_workbook
from data_loader import load_df, show_published_timestamp


st.set_page_config(page_title="Paramount KPI Portal", layout="wide")
st.title("Paramount KPI Portal")

# Auto-sync the Excel workbook into data/current.xlsx (hands-free path)
# This uses Streamlit Cloud Secrets:
# - DATA_XLSX_URL
# - optional DATA_AUTH_HEADER
updated, msg = ensure_latest_workbook()
st.caption("Auto data sync: " + msg)

# Show the timestamp for whatever file is currently on disk
show_published_timestamp()

# Quick sanity preview (kept from your original)
df = load_df()
st.write("Use the left sidebar to switch between pages as we add them.")
st.divider()

st.subheader("Quick preview")
st.dataframe(df.head(25), use_container_width=True)

st.subheader("Columns")
st.write(list(df.columns))
