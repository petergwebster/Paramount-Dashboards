import streamlit as st
from pathlib import Path
from data_loader import load_workbook_tables

st.set_page_config(page_title="Data", layout="wide")

st.markdown("## Data Loader")
st.markdown("**VERSION STAMP: 90_Data.py / main**")

with st.sidebar:
    st.header("Source")
    xlsx_path_str = st.text_input("Workbook path", value="data/current.xlsx")
    min_text_cells_val = st.number_input(
        "Min text cells threshold",
        min_value=0,
        max_value=50,
        value=4,
        step=1,
    )

st.markdown("### Action")
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

st.markdown("### Current in-memory status")

tables_existing = st.session_state.get("tables")
meta_existing = st.session_state.get("tables_meta")

if tables_existing is None:
    st.info("No tables in memory yet. Click Load workbook.")
else:
    st.write("Workbook path")
    st.write(st.session_state.get("workbook_path"))

    st.write("Number of tables")
    st.write(len(tables_existing))

    st.write("First 30 table keys")
    st.write(sorted(list(tables_existing.keys()))[:30])

    if meta_existing is not None and meta_existing.shape[0] > 0:
        st.markdown("#### Table metadata (head)")
        st.dataframe(meta_existing.head(50), use_container_width=True)

        if "note" in meta_existing.columns:
            fallback_rows = meta_existing[meta_existing["note"] == "fallback_all_sheets"]
            if fallback_rows.shape[0] > 0:
                st.warning("Fallback mode is active: returning all sheets because the table filter found 0 tables.")
