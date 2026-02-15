import streamlit as st
from pathlib import Path
import pandas as pd

from data_loader import load_workbook_tables
from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Data Loader Verification")

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
xlsx_path = data_dir / "current.xlsx"

st.markdown("#### Auto-sync status")
try:
    updated, msg = ensure_latest_workbook()
    st.caption("Auto data sync: " + msg)
    if updated:
        st.cache_data.clear()
except Exception as exc:
    st.warning("Auto-sync failed (upload still works).")
    st.exception(exc)

st.markdown("#### Manual upload override (optional)")
uploaded = st.file_uploader("Upload Excel (.xlsx) to override current.xlsx", type=["xlsx"])
if uploaded is not None:
    xlsx_path.write_bytes(uploaded.getbuffer())
    st.cache_data.clear()
    st.success("Saved to " + str(xlsx_path))

if not xlsx_path.exists():
    st.info("No workbook found yet. Either fix auto-sync or upload a workbook above.")
    st.stop()

mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit="s")
file_size_mb = round(xlsx_path.stat().st_size / (1024 * 1024), 2)

st.markdown("#### Current file on server")
st.write(str(xlsx_path))
st.write("Last modified")
st.write(mod_ts)
st.write("Size (MB)")
st.write(file_size_mb)

st.markdown("#### Step 2: Choose tabs and preview cleaning")
min_text_cells = st.slider(
    "Header detection sensitivity (min non-empty cells in header row)",
    2,
    10,
    4,
)

try:
    xl_obj = pd.ExcelFile(xlsx_path)
    all_sheets = xl_obj.sheet_names
except Exception as exc:
    st.error("Failed to read workbook as Excel.")
    st.exception(exc)
    st.stop()

if len(all_sheets) == 0:
    st.warning("Workbook has no sheets.")
    st.stop()

selected = st.multiselect("Sheets to load", options=all_sheets, default=all_sheets)

if st.button("Load and preview selected tabs"):
    try:
        tables, meta_df, _ = load_workbook_tables(
            str(xlsx_path),
            selected_sheets=selected,
            min_text_cells=min_text_cells
        )
    except Exception as exc:
        st.error("Failed while cleaning/loading selected sheets.")
        st.exception(exc)
        st.stop()

    st.markdown("### Cleaning summary")
    st.dataframe(meta_df, use_container_width=True)

    st.markdown("### Previews")
    for sn in selected:
        st.markdown("#### " + sn)
        df_prev = tables.get(sn)
        if df_prev is None or df_prev.shape[0] == 0:
            st.warning("This sheet returned no rows.")
            continue

        st.write("Shape")
        st.write(df_prev.shape)
        st.dataframe(df_prev.head(25), use_container_width=True)
