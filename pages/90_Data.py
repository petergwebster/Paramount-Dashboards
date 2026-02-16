from pathlib import Path
import io
import zipfile

import pandas as pd
import streamlit as st

from data_sync import ensure_latest_workbook
from data_loader import load_workbook_tables, DEFAULT_SHEET_WHITELIST


st.set_page_config(page_title="Data", layout="wide")
st.title("Data")


def _zip_selected_tables_as_csv_bytes(tables_dict, sheet_names):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for sheet_name in sheet_names:
            key = "sheet::" + sheet_name
            if key not in tables_dict:
                continue
            df_val = tables_dict[key]
            csv_bytes = df_val.to_csv(index=False).encode("utf-8")
            safe_name = "".join([c if c.isalnum() or c in [" ", "-", "_"] else "_" for c in sheet_name]).strip()
            if safe_name == "":
                safe_name = "sheet"
            zf.writestr(safe_name + ".csv", csv_bytes)
    zip_buf.seek(0)
    return zip_buf.getvalue()


# Always sync workbook from Secrets URL (this is the baked-in behavior)
workbook_path = ensure_latest_workbook()
workbook_path = Path(workbook_path)

if not workbook_path.exists():
    st.error("Workbook not found at " + str(workbook_path))
    st.stop()

file_size_mb = round(workbook_path.stat().st_size / (1024 * 1024), 2)
mod_ts = pd.to_datetime(workbook_path.stat().st_mtime, unit="s")

st.caption("Workbook source")
st.code("DATA_XLSX_URL (Streamlit secrets) -> downloaded to: " + str(workbook_path))

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.caption("Last modified")
    st.write(mod_ts)
with col_b:
    st.caption("Size MB")
    st.write(file_size_mb)
with col_c:
    st.caption("Local path")
    st.write(str(workbook_path))

st.divider()


# Names-only call: fast. Requires your data_loader.py to support selected_sheets == [] returning sheet names.
try:
    _, _, all_sheets = load_workbook_tables(str(workbook_path), selected_sheets=[])
except Exception:
    # Fallback: if your loader doesn't support names-only yet, just read sheet names directly
    xl_tmp = pd.ExcelFile(str(workbook_path))
    all_sheets = xl_tmp.sheet_names

default_selected = [s for s in DEFAULT_SHEET_WHITELIST if s in all_sheets]
if len(default_selected) == 0:
    default_selected = all_sheets[:5]

selected_sheets = st.multiselect(
    "Select sheets to load",
    options=all_sheets,
    default=default_selected,
)

col1, col2, col3 = st.columns(3)
with col1:
    min_text_cells = st.slider("Header detection sensitivity", min_value=2, max_value=10, value=4)
with col2:
    remove_pivot_totals = st.checkbox("Remove subtotal/total rows", value=True)
with col3:
    preview_rows = st.number_input("Preview rows", min_value=10, max_value=500, value=50, step=10)

st.divider()


# Load tables when user asks (prevents doing heavy work on every rerun)
load_now = st.button("Load selected sheets", type="primary")

if load_now:
    tables, meta_df, _ = load_workbook_tables(
        str(workbook_path),
        selected_sheets=selected_sheets,
        min_text_cells=int(min_text_cells),
        remove_pivot_totals=bool(remove_pivot_totals),
    )

    st.subheader("Loaded sheets summary")
    st.dataframe(meta_df, use_container_width=True, height=260)

    st.subheader("Download")
    zip_bytes = _zip_selected_tables_as_csv_bytes(tables, selected_sheets)
    st.download_button(
        "Download selected sheets as CSV ZIP",
        data=zip_bytes,
        file_name="selected_sheets_csv.zip",
        mime="application/zip",
        use_container_width=True,
    )

    st.subheader("Previews")
    for sheet_name in selected_sheets:
        key = "sheet::" + sheet_name
        if key not in tables:
            st.warning("No table loaded for " + sheet_name)
            continue

        df_prev = tables[key]
        with st.expander(sheet_name + "   rows " + str(df_prev.shape[0]) + "   cols " + str(df_prev.shape[1]), expanded=False):
            st.dataframe(df_prev.head(int(preview_rows)), use_container_width=True)
