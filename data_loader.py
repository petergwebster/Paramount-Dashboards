from pathlib import Path
import pandas as pd

# Make this module importable even in non-Streamlit contexts (tests, notebooks)
try:
    import streamlit as st
except Exception:
    class _StubStreamlit:
        def cache_data(self, *args, **kwargs):
            def _decor(fn):
                return fn
            return _decor

        def write(self, *args, **kwargs):
            return None

        def caption(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

    st = _StubStreamlit()

DEFAULT_DATA_PATH = Path("data/current.xlsx")

# Default sheet whitelist (your 7 dashboard tabs)
DEFAULT_SHEET_WHITELIST = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

# Optional aliases so the app stays stable if Excel tab names drift
SHEET_ALIASES = {
    "Witten Produced Invoiced": "Written Produced Invoiced",
    "YTD Plan vs Actual": "YTD Plan vs Act",
    "YTD Plan vs Actuals": "YTD Plan vs Act",
    "Production WIP": "WIP",
}

def _normalize_sheet_name(name_val):
    name_str = str(name_val).strip()
    if name_str in SHEET_ALIASES:
        return SHEET_ALIASES[name_str]
    return name_str

def _row_text_count(row_vals):
    ser = row_vals.astype(str).str.strip()
    ser = ser.replace("", "")
    return int(ser.ne("").sum())

def _drop_excel_junk_columns(df_in):
    if df_in is None or not hasattr(df_in, "columns"):
        return df_in

    bad_cols = []
    for c in df_in.columns:
        c_str = str(c).strip().lower()
        if c_str == "" or c_str.startswith(".") or c_str.startswith("unnamed"):
            bad_cols.append(c)

    if len(bad_cols) > 0:
        return df_in.drop(columns=bad_cols)
    return df_in

def _remove_pivot_totals(df_in):
    # Conservative but effective:
    # If ANY object column contains 'total' or 'grand total' (case-insensitive), drop that row.
    if df_in is None:
        return df_in
    if not hasattr(df_in, "shape"):
        return df_in
    if df_in.shape[0] == 0:
        return df_in

    df = df_in.copy()

    obj_cols = []
    for c in df.columns:
        try:
            if df[c].dtype == object or str(df[c].dtype) == "object":
                obj_cols.append(c)
        except Exception:
            continue

    if len(obj_cols) == 0:
        return df

    mask_total = pd.Series(False, index=df.index)
    for c in obj_cols:
        col_ser = df[c].astype(str).str.strip().str.lower()
        mask_total = mask_total | col_ser.str.contains("grand total", na=False)
        mask_total = mask_total | col_ser.str.contains("total", na=False)

    return df.loc[~mask_total].copy()

def clean_pivot_export_sheet(xl_obj, sheet_name, min_text_cells=4, remove_totals=True):
    # Reads an Excel pivot-export-like sheet where the header row isn't guaranteed to be row 1
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_text_counts = df_raw.apply(lambda r: _row_text_count(r), axis=1)

    # Find first row that looks like a header row
    header_row_idx = int((row_text_counts >= min_text_cells).idxmax())

    new_cols = [str(x).strip() for x in df_raw.iloc[header_row_idx].tolist()]
    df_clean = df_raw.iloc[header_row_idx + 1 :].copy()
    df_clean.columns = new_cols

    # Drop fully empty rows
    nonempty_row_mask = df_clean.apply(lambda r: _row_text_count(r) > 0, axis=1)
    df_clean = df_clean.loc[nonempty_row_mask].reset_index(drop=True)

    # Drop fully empty cols
    nonempty_col_mask = df_clean.apply(
        lambda c: c.astype(str).str.strip().replace("", "").ne("").any(), axis=0
    )
    df_clean = df_clean.loc[:, nonempty_col_mask].copy()

    # Drop Excel spillover columns like .1 / Unnamed
    df_clean = _drop_excel_junk_columns(df_clean)

    # Remove subtotal/total rows from pivot exports
    if remove_totals:
        df_clean = _remove_pivot_totals(df_clean)

    return df_clean

@st.cache_data(show_spinner=False)
def load_workbook_tables(
    excel_path,
    selected_sheets=None,
    min_text_cells=4,
    sheet_whitelist=None,
    remove_pivot_totals=True,
):
    xl = pd.ExcelFile(excel_path)
    all_sheets = xl.sheet_names

    whitelist = DEFAULT_SHEET_WHITELIST if sheet_whitelist is None else sheet_whitelist
    whitelist = [_normalize_sheet_name(x) for x in whitelist]

    # IMPORTANT: if selected_sheets is explicitly [], treat as "names-only"
    # This avoids loading/cleaning and prevents crashes when the UI just wants sheet names.
    if selected_sheets == []:
        meta_df = pd.DataFrame(columns=["key", "sheet_name", "rows", "cols"])
        return {}, meta_df, all_sheets

    # selected_sheets None means: use whitelist
    if selected_sheets is None:
        requested = whitelist
    else:
        requested = [_normalize_sheet_name(x) for x in selected_sheets]

    # Only load sheets that exist
    requested = [s for s in requested if s in all_sheets]

    tables = {}
    meta_rows = []

    for sheet_name in requested:
        key = "sheet::" + sheet_name
        try:
            df_clean = clean_pivot_export_sheet(
                xl,
                sheet_name,
                min_text_cells=min_text_cells,
                remove_totals=remove_pivot_totals,
            )
            tables[key] = df_clean
            meta_rows.append(
                {
                    "key": key,
                    "sheet_name": sheet_name,
                    "rows": int(df_clean.shape[0]),
                    "cols": int(df_clean.shape[1]),
                }
            )
        except Exception as e:
            meta_rows.append(
                {
                    "key": key,
                    "sheet_name": sheet_name,
                    "rows": 0,
                    "cols": 0,
                    "error": str(e),
                }
            )

    if len(meta_rows) == 0:
        meta_df = pd.DataFrame(columns=["key", "sheet_name", "rows", "cols"])
    else:
        meta_df = pd.DataFrame(meta_rows).sort_values(["sheet_name"]).reset_index(drop=True)

    return tables, meta_df, all_sheets

def show_published_timestamp(excel_path=None):
    # Backwards-compatible helper expected by streamlit_app.py
    # Shows last-modified time and size for the locally present workbook.
    if excel_path is None:
        excel_path = DEFAULT_DATA_PATH

    excel_path = Path(excel_path)

    if not excel_path.exists():
        try:
            st.warning("Workbook not found at " + str(excel_path))
        except Exception:
            pass
        return None

    mod_ts = pd.to_datetime(excel_path.stat().st_mtime, unit="s")
    file_size_mb = round(excel_path.stat().st_size / (1024 * 1024), 2)

    try:
        st.caption("Data workbook")
        st.write(str(excel_path))
        st.write("Last modified")
        st.write(mod_ts)
        st.write("Size MB")
        st.write(file_size_mb)
    except Exception:
        pass

    return {"path": str(excel_path), "last_modified": mod_ts, "size_mb": file_size_mb}
