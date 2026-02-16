import streamlit as st
from data_loader import load_workbook_tables_from_url

st.set_page_config(page_title="Data", layout="wide")

st.markdown("## Data Loader")
st.markdown("**Source: GitHub Release URL from Streamlit Secrets**")

xlsx_url_default = ""
if "DATA_XLSX_URL" in st.secrets:
    xlsx_url_default = st.secrets["DATA_XLSX_URL"]

with st.sidebar:
    st.header("Source")
    xlsx_url = st.text_input("DATA_XLSX_URL", value=xlsx_url_default)
    min_text_cells_val = st.number_input(
        "Min text cells threshold",
        min_value=0,
        max_value=50,
        value=4,
        step=1,
    )

st.markdown("### Action")
load_clicked = st.button("Load workbook from release URL", type="primary")

if load_clicked:
    if xlsx_url is None or str(xlsx_url).strip() == "":
        st.error("DATA_XLSX_URL is empty. Add it in Streamlit Secrets or paste it here.")
        st.stop()

    with st.spinner("Downloading and loading workbook from " + str(xlsx_url)):
        tables, meta_df, all_sheets = load_workbook_tables_from_url(
            str(xlsx_url),
            selected_sheets=[],
            min_text_cells=int(min_text_cells_val),
        )

    st.session_state["tables"] = tables
    st.session_state["tables_meta"] = meta_df
    st.session_state["tables_all_sheets"] = all_sheets
    st.session_state["workbook_source_url"] = str(xlsx_url)

    st.success("Loaded workbook from release URL and saved tables to session_state['tables'].")

st.markdown("### Current in-memory status")

tables_existing = st.session_state.get("tables")
meta_existing = st.session_state.get("tables_meta")

st.write("Workbook source url")
st.write(st.session_state.get("workbook_source_url"))

if tables_existing is None:
    st.info("No tables in memory yet. Click Load workbook from release URL.")
else:
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
