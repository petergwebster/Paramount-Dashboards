import streamlit as st
import pandas as pd
from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

st.header("Workbook source")

st.write("DATA_XLSX_URL")
st.code(str(st.secrets.get("DATA_XLSX_URL", "")))

workbook_path = ensure_latest_workbook(ttl_seconds=0)

st.write("Workbook path used")
st.code(str(workbook_path))

xl = pd.ExcelFile(str(workbook_path))
sheet_names = xl.sheet_names

st.write("Sheets detected")
st.write(sheet_names)

st.header("Load sheets")

selected_sheets = st.multiselect(
    "Select sheets to load",
    options=sheet_names,
    default=sheet_names,
)

max_rows = st.number_input("Preview rows per sheet", min_value=5, max_value=200, value=20, step=5)

if len(selected_sheets) == 0:
    st.info("Pick at least one sheet above.")
else:
    for sheet_val in selected_sheets:
        st.subheader(sheet_val)
        df_sheet = pd.read_excel(str(workbook_path), sheet_name=sheet_val)
        st.dataframe(df_sheet.head(int(max_rows)), use_container_width=True)
