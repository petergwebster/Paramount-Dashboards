import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")

st.caption("If you can see this, 01_Cockpit.py parsed successfully.")

st.subheader("Session state keys")
st.write(sorted(list(st.session_state.keys())))

if "sheets_raw" not in st.session_state:
    st.warning("No sheets loaded yet. Go to the Data page and click Load and preview selected tabs.")
    st.stop()

tables = st.session_state["sheets_raw"]

if not isinstance(tables, dict) or len(tables) == 0:
    st.warning("sheets_raw exists but is empty or not a dict.")
    st.write(type(tables))
    st.stop()

st.success("Found " + str(len(tables)) + " sheets in st.session_state[sheets_raw].")

st.subheader("Sheet names")
st.write(sorted(list(tables.keys())))

first_name = sorted(list(tables.keys()))[0]
st.subheader("Preview: " + first_name)
st.dataframe(tables[first_name].head(25), use_container_width=True)
