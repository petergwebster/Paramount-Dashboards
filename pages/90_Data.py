import streamlit as st
from pathlib import Path
from data_loader import load_workbook_tables

st.set_page_config(page_title="Data", layout="wide")

st.markdown("## Data Loader")

with st.sidebar:
    st.header("Source")
    xlsx_path_str = st.text_input("Workbook path", value="data/current.xlsx")
    min_text_cells_val = st.number_input("Min text cells threshold", min_value=0, max_value=50, value=4, step=1)

load_clicked = st.button("Load workbook", type="primary")

if load_clicked:
    xlsx_path = Path(xlsx_path_str)

    if not xlsx_path.exists():
        st.error("File not found at " + str(xlsx_path))
        st.stop()

    with st.spinner("Loading workbook and extracting tables"):
        tables, meta_df, all_sheets = load_workbook_tables(
            str(xlsx_path),
            selected_sheets=[],
            min_text_cells=int(min_text_cells_val),
        )

    st.session_state["tables"] = tables
    st.session_state["tables_meta"] = meta_df
    st.session_state["tables_all_sheets"] = all_sheets
    st.session_state["workbook_path"] = str(xlsx_path)

    st.success("Loaded workbook and saved cleaned tables to session_state as tables")

tables_existing = st.session_state.get("tables")

st.markdown("### Current in-memory status")
if tables_existing is None:
    st.info("No tables in memory yet. Click Load workbook.")
else:
    st.write("Workbook path")
    st.write(st.session_state.get("workbook_path"))

    st.write("Number of tables")
    st.write(len(tables_existing))

    st.write("First 30 table keys")
    st.write(sorted(list(tables_existing.keys()))[:30])
