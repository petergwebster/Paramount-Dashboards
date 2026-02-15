import streamlit as st
from pathlib import Path
import pandas as pd

from data_sync import ensure_latest_workbook
from data_loader import load_workbook_tables

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

xlsx_path = Path("data") / "current.xlsx"

try:
    updated, msg = ensure_latest_workbook()
    st.caption("Auto data sync: " + str(msg))
    if updated:
        st.cache_data.clear()
except Exception as exc:
    st.warning("Auto-sync failed. Using whatever workbook is currently on disk.")
    st.exception(exc)

st.markdown("#### Manual upload override (optional)")
uploaded = st.file_uploader("Upload a workbook (.xlsx) to override current.xlsx", type=["xlsx"])
if uploaded is not None:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    xlsx_path.write_bytes(uploaded.getbuffer())
    st.cache_data.clear()

if not xlsx_path.exists():
    st.error("Missing " + str(xlsx_path) + ". Add a workbook at data/current.xlsx to proceed.")
    st.stop()

mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit="s")
file_size_mb = round(xlsx_path.stat().st_size / (1024 * 1024), 2)

st.markdown("**Current file**")
st.write(str(xlsx_path))
st.write("Last modified")
st.write(mod_ts)
st.write("Size MB")
st.write(file_size_mb)

_, meta_all, all_sheets = load_workbook_tables(str(xlsx_path), selected_sheets=[])

st.markdown("**Select which tabs you want the dashboard to use**")
selected = st.multiselect("Sheets", options=all_sheets, default=all_sheets)

min_text_cells = st.slider("Header detection sensitivity (min non-empty cells in header row)", 2, 10, 4)

if st.button("Load and preview selected tabs"):
    tables, meta_df, _ = load_workbook_tables(
        str(xlsx_path),
        selected_sheets=selected,
        min_text_cells=min_text_cells
    )

    # IMPORTANT: Persist for other pages (Cockpit, Explore, etc.)
    st.session_state["sheets_raw"] = tables
    st.session_state["meta_df"] = meta_df
    st.session_state["selected_sheets"] = selected
    st.session_state["xlsx_path"] = str(xlsx_path)

    st.success("Loaded " + str(len(tables)) + " sheets into st.session_state[sheets_raw].")

    st.markdown("### Sheet cleaning summary")
    st.dataframe(meta_df, use_container_width=True)

    st.markdown("### Previews")
    for sn in selected:
        st.markdown("#### " + sn)
        if sn not in tables:
            st.warning("No table loaded for this sheet")
            continue

        df_prev = tables[sn]
        st.write("Shape")
        st.write(df_prev.shape)
        st.dataframe(df_prev.head(25), use_container_width=True)

        csv_bytes = df_prev.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download cleaned CSV for " + sn,
            data=csv_bytes,
            file_name=sn.replace("/", "_") + ".csv",
            mime="text/csv"
        )
else:
    if "sheets_raw" in st.session_state and isinstance(st.session_state["sheets_raw"], dict):
        st.info("Already loaded in session: " + str(len(st.session_state["sheets_raw"])) + " sheets.")
    else:
        st.info("Click Load and preview selected tabs to load data into the session.")
