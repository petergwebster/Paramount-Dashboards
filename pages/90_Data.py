import streamlit as st
from pathlib import Path
import pandas as pd

from data_loader import load_workbook_tables, DEFAULT_SHEET_WHITELIST

st.set_page_config(page_title="Data", layout="wide")
st.title("Data Loader Verification")

xlsx_path = Path("data/current.xlsx")

if not xlsx_path.exists():
    st.error("Missing data/current.xlsx. Add a workbook at data/current.xlsx to proceed.")
    st.stop()

mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit="s")
file_size_mb = round(xlsx_path.stat().st_size / (1024 * 1024), 2)

st.markdown("**Current file**")
st.write(str(xlsx_path))
st.write("Last modified")
st.write(mod_ts)
st.write("Size MB")
st.write(file_size_mb)

# Load sheet names quickly
_, _, all_sheets = load_workbook_tables(str(xlsx_path), selected_sheets=[])

default_selected = [s for s in DEFAULT_SHEET_WHITELIST if s in all_sheets]

st.markdown("**Select which tabs you want the dashboard to use**")
selected = st.multiselect("Sheets", options=all_sheets, default=default_selected)

min_text_cells = st.slider(
    "Header detection sensitivity (min non-empty cells in header row)",
    2, 10, 4
)

remove_pivot_totals = st.checkbox("Remove pivot subtotal/total rows", value=True)

if st.button("Load and preview selected tabs"):
    tables, meta_df, _ = load_workbook_tables(
        str(xlsx_path),
        selected_sheets=selected,
        min_text_cells=min_text_cells,
        remove_pivot_totals=remove_pivot_totals,
    )

    st.session_state["tables"] = tables
    st.session_state["meta_df"] = meta_df

    st.markdown("### Sheet cleaning summary")
    st.dataframe(meta_df, use_container_width=True)

    st.markdown("### Previews")
    for sn in selected:
        key = "sheet::" + sn
        st.markdown("#### " + sn)

        if key not in tables:
            st.warning("No table loaded for this sheet")
            continue

        df_prev = tables[key]
        st.write("Shape")
        st.write(df_prev.shape)
        st.dataframe(df_prev.head(25), use_container_width=True)
