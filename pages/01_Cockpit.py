import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")

st.title("Cockpit")

tables = st.session_state.get("tables")

if tables is None:
    st.warning("No data loaded yet. Go to the Data page and click Load workbook.")
    st.stop()

st.markdown("#### Tables available (from memory)")
st.write("Total tables")
st.write(len(tables))

table_keys = sorted(list(tables.keys()))
st.write("First 60 table keys")
st.write(table_keys[:60])

st.markdown("#### Next step")
st.write("Pick the correct weekly table key from the list above. Then we will wire a single Weekly metric and one chart.")
