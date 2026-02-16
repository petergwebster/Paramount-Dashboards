from pathlib import Path
import datetime as dt
import re
import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

ALLOWED_SHEETS = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

def _clean_columns(cols_val):
    clean_cols = []
    for c in cols_val:
        c_str = str(c)
        c_str = re.sub(r"\s+", " ", c_str).strip()
        clean_cols.append(c_str)
    return clean_cols

def _drop_unnamed_and_empty_columns(df_val):
    cols_str = df_val.columns.astype(str)
    keep_mask = ~cols_str.str.match(r"^Unnamed")
    df_val = df_val.loc[:, keep_mask]
    df_val = df_val.dropna(axis=1, how="all")
    return df_val

def _score_header_row(row_vals):
    vals = ["" if pd.isna(x) else str(x).strip() for x in row_vals]
    non_empty = [v for v in vals if v != ""]
    if len(non_empty) == 0:
        return 0
    unique_count = len(set(non_empty))
    score = len(non_empty) + unique_count
    return score

def _detect_header_row(excel_path, sheet_name, max_scan_rows=25):
    preview_df = pd.read_excel(
        str(excel_path),
        sheet_name=sheet_name,
        header=None,
        nrows=int(max_scan_rows),
        engine=None
    )

    best_idx = 0
    best_score = -1
    for idx_val in range(preview_df.shape[0]):
        row_vals = preview_df.iloc[idx_val].tolist()
        score_val = _score_header_row(row_vals)
        if score_val > best_score:
            best_score = score_val
            best_idx = idx_val

    return int(best_idx)

@st.cache_data(show_spinner=False)
def _read_sheet_cached(excel_path_str, sheet_name, header_row_idx):
    df_val = pd.read_excel(
        excel_path_str,
        sheet_name=sheet_name,
        header=int(header_row_idx)
    )
    df_val.columns = _clean_columns(df_val.columns)
    df_val = _drop_unnamed_and_empty_columns(df_val)
    return df_val

with st.expander("Workbook source", expanded=False):
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

workbook_path = ensure_latest_workbook(ttl_seconds=0)
xl_obj = pd.ExcelFile(str(workbook_path))
all_sheet_names = xl_obj.sheet_names

allowed_present = [s for s in all_sheet_names if s in ALLOWED_SHEETS]
allowed_missing = [s for s in ALLOWED_SHEETS if s not in all_sheet_names]

with st.expander("Sheet visibility (debug)", expanded=False):
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

show_raw_header_detection = st.checkbox("Show header detection details", value=False)

if len(selected_sheets) == 0:
    st.info("Select at least one sheet above.")
else:
    for sheet_val in selected_sheets:
        st.subheader(sheet_val)

        header_row_idx = _detect_header_row(workbook_path, sheet_val, max_scan_rows=25)

        if show_raw_header_detection:
            st.caption("Detected header row index (0-based)")
            st.code(str(header_row_idx))

            preview_raw = pd.read_excel(
                str(workbook_path),
                sheet_name=sheet_val,
                header=None,
                nrows=int(header_row_idx + 5)
            )
            st.caption("Top rows (raw) used for header detection")
            st.dataframe(preview_raw, use_container_width=True)

        df_sheet = _read_sheet_cached(str(workbook_path), sheet_val, header_row_idx)

        st.caption("Preview (cleaned)")
        st.dataframe(df_sheet.head(int(max_rows)), use_container_width=True)
