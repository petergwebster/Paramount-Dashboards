import streamlit as st

def require_tables():
    tables = st.session_state.get("sheets_raw")
    if tables is None or not isinstance(tables, dict) or len(tables) == 0:
        st.warning("No data loaded yet. Go to the Data page and click Load and preview selected tabs.")
        st.stop()
    return tables

def _norm_name(name_in):
    return "".join([c.lower() for c in str(name_in).strip() if c.isalnum()])

def get_table(tables, desired_name):
    desired_norm = _norm_name(desired_name)

    if desired_name in tables:
        return tables[desired_name], desired_name

    for k in tables.keys():
        if _norm_name(k) == desired_norm:
            return tables[k], k

    for k in tables.keys():
        if desired_norm in _norm_name(k):
            return tables[k], k

    return None, None
