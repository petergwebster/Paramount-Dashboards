import streamlit as st

st.set_page_config(page_title="Home", layout="wide")

st.title("Dashboard Home")

st.write("Use Data to load the workbook, then Cockpit to view KPIs. Debug is for troubleshooting.")

st.page_link("pages/90_Data.py", label="1) Load Data", icon="🧪")
st.page_link("pages/01_Cockpit.py", label="2) Open Cockpit", icon="📊")
st.page_link("pages/99_Debug.py", label="Debug", icon="🛠️")
