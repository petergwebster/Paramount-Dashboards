import streamlit as st
from pathlib import Path
from data_loader import load_workbook_tables

st.set_page_config(page_title="Data", layout="wide")

st.title("Data Loader")

st.write("Load an Excel workbook, extract table-like sheets, and store cleaned tables in memory for the Cockpit page.")

with st.sidebar:
    st.header("Source")
    default_path_str = "data/current.xlsx"
    xlsx_path_str = st.text_input("Workbook path", value=default_path_str)
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

st.markdown("#### Current in-memory status")

tables_existing = st.session_state.get("tables")
workbook_path_existing = st.session_state.get("workbook_path")

if tables_existing is None:
    st.info("No tables in memory yet. Click Load workbook.")
else:
    st.write("Workbook path")
    st.write(workbook_path_existing)

    st.write("Number of tables")
    st.write(len(tables_existing))

    st.write("First 30 table keys")
    table_keys = sorted(list(tables_existing.keys()))
    st.write(table_keys[:30])

    meta_existing = st.session_state.get("tables_meta")
    if meta_existing is not None:
        st.markdown("#### Table metadata (head)")
        st.dataframe(meta_existing.head(20), use_container_width=True)
