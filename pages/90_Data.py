import streamlit as st
from pathlib import Path
import pandas as pd

from data_sync import ensure_latest_workbook
from data_loader import load_workbook_tables, DEFAULT_SHEET_WHITELIST

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

# 1. Get the real workbook via secrets-driven sync
workbook_path_val = ensure_latest_workbook()
if isinstance(workbook_path_val, str):
    workbook_path = Path(workbook_path_val)
else:
    workbook_path = workbook_path_val

if workbook_path is None or not Path(workbook_path).exists():
    st.error("Workbook not found. ensure_latest_workbook() returned: " + str(workbook_path))
    st.stop()

workbook_path = Path(workbook_path)

# 2. Show workbook info
mod_ts = pd.to_datetime(workbook_path.stat().st_mtime, unit="s")
file_size_mb = round(workbook_path.stat().st_size / (1024 * 1024), 2)

top_cols = st.columns([2, 1, 1])
with top_cols[0]:
    st.caption("Workbook path")
    st.code(str(workbook_path))
with top_cols[1]:
    st.caption("Last modified")
    st.write(mod_ts)
with top_cols[2]:
    st.caption("Size (MB)")
    st.write(file_size_mb)

st.divider()

# 3. Get list of sheets (fast)
_, _, all_sheets = load_workbook_tables(str(workbook_path), selected_sheets=[])

default_selected = [s for s in DEFAULT_SHEET_WHITELIST if s in all_sheets]

st.subheader("Sheets")
selected_sheets = st.multiselect(
    "Select the sheets the dashboard should load",
    options=all_sheets,
    default=default_selected,
)

control_cols = st.columns([1, 1, 2])
with control_cols[0]:
    min_text_cells = st.slider(
        "Header detection sensitivity",
        min_value=2,
        max_value=10,
        value=4,
    )
with control_cols[1]:
    remove_pivot_totals = st.checkbox("Remove subtotal/total rows", value=True)
with control_cols[2]:
    st.caption("Keep selection to the 7 dashboard tabs for speed and consistency.")

st.divider()

# 4. Load and preview
if st.button("Load and preview selected tabs", type="primary"):
    if len(selected_sheets) == 0:
        st.warning("Select at least 1 sheet.")
        st.stop()

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
        label = f"{sn}  ({df_prev.shape[0]} rows, {df_prev.shape[1]} cols)"
        with st.expander(label, expanded=False):
            st.dataframe(df_prev
