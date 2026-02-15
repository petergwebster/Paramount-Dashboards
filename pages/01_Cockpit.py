import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")

st.caption("Cockpit parsed successfully.")

st.subheader("Session state keys")
st.write(sorted(list(st.session_state.keys())))

tables = st.session_state.get("sheets_raw")

if tables is None:
    st.warning("No data loaded yet. Go to Data and click Load and preview selected tabs.")
    st.stop()

if not isinstance(tables, dict):
    st.error("sheets_raw exists but is not a dict.")
    st.write(type(tables))
    st.stop()

if len(tables) == 0:
    st.warning("sheets_raw is an empty dict.")
    st.stop()

st.success("Found " + str(len(tables)) + " sheets in st.session_state[sheets_raw].")

st.subheader("Sheet names")
sheet_names = sorted(list(tables.keys()))
st.write(sheet_names)

first_name = sheet_names[0]
st.subheader("Preview: " + first_name)
st.dataframe(tables[first_name].head(25), use_container_width=True)
