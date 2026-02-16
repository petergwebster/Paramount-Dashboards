import streamlit as st

from data_sync import ensure_latest_workbook
from data_loader import show_published_timestamp

st.set_page_config(page_title="Paramount Dashboards", layout="wide")

# Always sync early so every page uses the same local file
workbook_path = ensure_latest_workbook()

# Show timestamp info (keeps your existing behavior)
show_published_timestamp(workbook_path)

pg = st.navigation(
    [
        st.Page("pages/01_Cockpit.py", title="Cockpit"),
        st.Page("pages/90_Data.py", title="Data"),
    ]
)
pg.run()
