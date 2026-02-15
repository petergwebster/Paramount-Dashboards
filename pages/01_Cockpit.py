import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")

st.caption("Cockpit loaded successfully. (No syntax errors)")

st.subheader("Session state keys")
st.write(sorted(list(st.session_state.keys())))

possible_keys = ["sheets_raw", "sheets", "dfs", "dataframes", "sheet_previews"]
found_key = None
for key in possible_keys:
    maybe = st.session_state.get(key)
    if isinstance(maybe, dict) and len(maybe) > 0:
        found_key = key
        break

if found_key is None:
    st.warning("No sheets dict found yet. Go to the Data page first, then return here.")
else:
    st.success("Found sheets dict at st.session_state[" + found_key + "]")
    sheets_dict = st.session_state[found_key]
    st.write("Sheet names")
    st.write(sorted(list(sheets_dict.keys())))
