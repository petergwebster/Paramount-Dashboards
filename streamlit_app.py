import streamlit as st

from data_sync import ensure_latest_workbook
from data_loader import show_published_timestamp

st.set_page_config(page_title="Paramount Dashboards", layout="wide")

st.title("Paramount Dashboards")

# Auto-download the latest multi-tab workbook into data/current.xlsx
# This runs on every cold start and also on reruns (Streamlit behavior).
try:
    updated, msg = ensure_latest_workbook()
    st.caption("Auto data sync: " + msg)
    if updated:
        # If the underlying Excel changed, cached sheet-lists / tables must be invalidated
        st.cache_data.clear()
except Exception as exc:
    st.warning("Auto-sync failed. The app will use whatever is currently on disk.")
    st.exception(exc)

# Show timestamp/metadata about the local data file the app will read
show_published_timestamp()

st.markdown(
    """
Go to the **Data** page to:
- confirm the sheet list shows all workbook tabs
- preview cleaned outputs
- optionally upload an override workbook
"""
)
