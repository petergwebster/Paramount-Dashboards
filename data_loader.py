import pandas as pd
from pathlib import Path

# Allow importing this module even in environments without streamlit
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

    st = _StubStreamlit()


# -----------------------------
# Defaults / configuration
# -----------------------------

DEFAULT_DATA_PATH = Path("data/current.xlsx")

DEFAULT_SHEET_WHITELIST = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

SHEET_ALIASES = {
    "Witten Produced Invoiced": "Written Produced Invoiced",
    "YTD Plan vs Actual": "YTD Plan vs Act",
    "YTD Plan vs Actuals": "YTD Plan vs Act",
    "Production WIP": "WIP",
}


# -----------------------------
# Small helpers
# -----------------------------

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
        if c_str == "" or c_str == "" or c_str.startswith("") or c_str.startswith("unnamed"):
            bad_cols.append(c)

    if len(bad_cols) > 0:
        return df_in.drop(columns=bad_cols)
    return df_in

def _remove_pivot_totals(df_in):
    # Remove subtotal/total rows so we never double-count pivot exports.
    # Drops any row where any object column contains the substring "total".
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


# -----------------------------
# UI helper required by streamlit_app.py
# -----------------------------

def show_published_timestamp(xlsx_path=None):
    """
    Used by streamlit_app.py.
    Shows last modified time + file size for the workbook.
    Keeps UI stable even if file is missing.
    """
    if xlsx_path is None:
        xlsx_path = DEFAULT_DATA_PATH
    xlsx_path = Path(xlsx_path)

    if not xlsx_path.exists():
        try:
            st.info("Workbook not found at " + str(xlsx_path))
        except Exception:
            pass
        return None

    mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit="s")
    file_size_mb = round(xlsx_path.stat().st_size / (1024 * 1024), 2)

    try:
        st.caption("Workbook: " + str(xlsx_path))
        st.caption("Last modified: " + str(mod_ts))
        st.caption("Size (MB): " + str(file_size_mb))
    except Exception:
        pass

    return {"path": str(xlsx_path), "modified": mod_ts, "size_mb": file_size_mb}


# -----------------------------
# Main cleaning + loading
# -----------------------------

def clean_pivot_export_sheet(xl_obj, sheet_name, min_text_cells=4, remove_totals=True):
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_text_counts = df_raw.apply(lambda r: _row_text_count(r), axis=1)
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

    # Drop Excel junk columns and remove totals
    df_clean = _drop_excel_junk_columns(df_clean)

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

    if selected_sheets is None:
        selected_sheets = []

    if len(selected_sheets) > 0:
        requested = [_normalize_sheet_name(x) for x in selected_sheets]
    else:
        requested = whitelist

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

    meta_df = pd.DataFrame(meta_rows).sort_values(["sheet_name"]).reset_index(drop=True)
    return tables, meta_df, all_sheets
