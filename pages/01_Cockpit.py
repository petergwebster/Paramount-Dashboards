import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cockpit", layout="wide")

st.markdown("## Cockpit")
st.markdown("Reads from `st.session_state['tables']` only (no disk reload).")

workbook_path = st.session_state.get("workbook_path")
tables = st.session_state.get("tables")

st.markdown("### Current session state")

col_a, col_b = st.columns(2)
with col_a:
    st.write("Workbook path")
    st.write(workbook_path)

with col_b:
    if tables is None:
        st.write("Tables status")
        st.write("tables is None (not loaded)")
    else:
        st.write("Tables status")
        st.write("tables is dict with " + str(len(tables)) + " keys")

if tables is None or not isinstance(tables, dict) or len(tables) == 0:
    st.warning("No tables in memory. Go to the Data page and click Load workbook.")
    st.stop()

table_keys = sorted(list(tables.keys()))

st.markdown("### Keys currently in memory")
st.write(table_keys)

if "sheet::Sheet1" not in table_keys:
    st.info("`sheet::Sheet1` is not currently present. That usually means the workbook changed or the app restarted.")
    st.info("Pick one of the keys above from the dropdown to inspect it.")

with st.sidebar:
    st.header("Pick table")
    selected_key = st.selectbox("Table key", options=table_keys, index=0)

df = tables[selected_key]

st.markdown("### Selected table")
st.write("Key")
st.write(selected_key)

st.write("Shape")
st.write([int(df.shape[0]), int(df.shape[1])])

st.markdown("#### Preview")
st.dataframe(df.head(50), use_container_width=True)

st.markdown("#### Columns")
st.write([str(c) for c in df.columns])

st.markdown("#### Quick KPI")
non_null_total = int(df.notna().sum().sum())
total_cells = int(df.shape[0] * df.shape[1])
pct_filled = 0.0
if total_cells > 0:
    pct_filled = non_null_total / total_cells

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Rows", int(df.shape[0]))
with k2:
    st.metric("Cols", int(df.shape[1]))
with k3:
    st.metric("Filled cells percent", str(round(pct_filled * 100.0, 1)) + "%")
