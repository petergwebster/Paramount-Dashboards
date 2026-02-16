from pathlib import Path
import datetime as dt
import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

ALLOWED_SHEETS = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

with st.expander("Workbook source", expanded=True):
    url_val = st.secrets.get("DATA_XLSX_URL", "")
    st.write("DATA_XLSX_URL")
    st.code(str(url_val))

    workbook_path = ensure_latest_workbook(ttl_seconds=0)
    workbook_path_obj = Path(str(workbook_path))

    st.write("Local path")
    st.code(str(workbook_path_obj))

    if workbook_path_obj.exists():
        size_mb = workbook_path_obj.stat().st_size / (1024.0 * 1024.0)
        mtime = dt.datetime.fromtimestamp(workbook_path_obj.stat().st_mtime)
        st.write("Last modified")
        st.code(str(mtime))
        st.write("Size MB")
        st.code(str(round(size_mb, 1)))

xl_obj = pd.ExcelFile(str(workbook_path))
all_sheet_names = xl_obj.sheet_names

allowed_present = [s for s in all_sheet_names if s in ALLOWED_SHEETS]
allowed_missing = [s for s in ALLOWED_SHEETS if s not in all_sheet_names]

with st.expander("Sheet visibility (debug)", expanded=True):
    st.write("All sheets detected in workbook")
    st.write(all_sheet_names)

    st.write("Sheets exposed in UI")
    st.write(allowed_present)

    if len(allowed_missing) > 0:
        st.error("Workbook is missing required sheets: " + str(allowed_missing))
        st.stop()

st.header("Load data")
selected_sheets = st.multiselect(
    "Select sheets to load",
    options=allowed_present,
    default=allowed_present,
)

max_rows = st.number_input(
    "Preview rows per sheet",
    min_value=5,
    max_value=200,
    value=25,
    step=5,
)

if len(selected_sheets) == 0:
    st.info("Select at least one sheet above.")
else:
    for sheet_val in selected_sheets:
        st.subheader(sheet_val)
        df_sheet = pd.read_excel(str(workbook_path), sheet_name=sheet_val)
        st.dataframe(df_sheet.head(int(max_rows)), use_container_width=True)
