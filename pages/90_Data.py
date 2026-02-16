import streamlit as st
import pandas as pd
from pathlib import Path

from data_sync import ensure_latest_workbook
from data_loader import load_workbook_tables, DEFAULT_SHEET_WHITELIST

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

workbook_path_val = ensure_latest_workbook()
if isinstance(workbook_path_val, str):
    workbook_path = Path(workbook_path_val)
else:
    workbook_path = workbook_path_val

if workbook_path is None or not Path(workbook_path).exists():
    st.error("Workbook not found. ensure_latest_workbook() returned: " + str(workbook_path))
    st.stop()

workbook_path = Path(workbook_path)

mod_ts = pd.to_datetime(workbook_path.stat().st_mtime, unit="s")
file_size_mb = round(workbook_path.stat().st_size / (1024 * 1024), 2)

st.caption("Workbook source")
st.code("DATA_XLSX_URL (Streamlit secrets) -> downloaded to: " + str(workbook_path))
cols_info = st.columns(2)
with cols_info[0]:
    st.caption("Last modified")
    st.write(mod_ts)
with cols_info[1]:
    st.caption("Size (MB)")
    st.write(file_size_mb)

st.divider()

_, _, all_sheets = load_workbook_tables(str(workbook_path), selected_sheets=[])

default_selected = [s for s in DEFAULT_SHEET_WHITELIST if s in all_sheets]

selected_sheets = st.multiselect(
    "Sheets",
    options=all_sheets,
    default=default_selected,
)

cols_controls = st.columns(2)
with cols_controls[0]:
    min_text_cells = st.slider("Header detection sensitivity", 2, 10, 4)
with cols_controls[1]:
    remove_pivot_totals = st.checkbox("Remove subtotal/total rows", value=True)

if st.button("Load and preview selected tabs", type="primary"):
    tables, meta_df, _ = load_workbook_tables(
        str(workbook_path),
        selected_sheets=selected_sheets,
        min_text_cells=min_text_cells,
        remove_pivot_totals=remove_pivot_totals,
    )

    st.subheader("Summary")
    st.dataframe(meta_df, use_container_width=True, height=260)

    st.subheader("Previews")
    for sn in selected_sheets:
        key = "sheet::" + sn
        if key not in tables:
            with st.expander(sn, expanded=False):
                st.warning("No table loaded for this sheet.")
            continue

        df_prev = tables[key]
        exp_label = sn + "  (" + str(df_prev.shape[0]) + " rows, " + str(df_prev.shape[1]) + " cols)"
        with st.expander(exp_label, expanded=False):
            st.dataframe(df_prev.head(50), use_container_width=True)
