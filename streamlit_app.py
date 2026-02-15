import streamlit as st
from data_sync import ensure_latest_workbook
from data_loader import show_published_timestamp

st.set_page_config(page_title="Paramount Dashboards", layout="wide")
st.title("Paramount Dashboards")

try:
    updated, msg = ensure_latest_workbook()
    st.caption("Auto data sync: " + msg)
    if updated:
        st.cache_data.clear()
except Exception as exc:
    st.warning("Auto-sync failed.")
    st.exception(exc)

show_published_timestamp()
st.markdown("Use the Data page to preview tabs and validate cleaning.")
