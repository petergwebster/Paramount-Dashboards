import pandas as pd
from pathlib import Path

# Make this module importable even in non-Streamlit contexts (tests, notebooks)
try:
    import streamlit as st
except Exception:
    class _StubStreamlit:
        def cache_data(self, *args, **kwargs):
            def _decor(fn):
                return fn
            return _decor
    st = _StubStreamlit()

DATA_PATH_DEFAULT = Path("data/current.xlsx")

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
}


def _row_text_count(row_vals):
    ser = row_vals.astype(str).str.strip()
    ser = ser.replace("", "")
    return int(ser.ne("").sum())


def _normalize_sheet_name(name_val):
    name_str = str(name_val).strip()
    if name_str in SHEET_ALIASES:
        return SHEET_ALIASES[name_str]
    return name_str


def _remove_pivot_totals(df_in):
    """
    Remove subtotal/total rows so we never double-count pivot exports.

    Conservative rule (by design):
    - If ANY object column contains 'total' or 'grand total' (case-insensitive),
      drop that row.
    """
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
    """
    Reads an Excel pivot-export-like sheet where the header row isn't guaranteed
    to be row 1, finds the header, and returns a clean rectangular table.
    """
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_text_counts = df_raw.apply(lambda r: _row_text_count(r), axis=1)
    header_row_idx = int((row_text_counts >= min_text_cells).idxmax())

    new_cols = [str(x).strip() for x in df_raw.iloc[header_row_idx].tolist()]
    df_clean = df_raw.iloc[header_row_idx + 1 :].copy()
    df_clean.columns = new_cols

    # Drop fully empty rows
    nonempty_row_mask = df_clean.apply(lambda r: _row_text_count(r) > 0, axis=1)
    df_clean = df_clean.loc[nonempty_row_mask].reset_index(drop=True)

    # Drop fully empty columns
    nonempty_col_mask = df_clean.apply(
        lambda c: c.astype(str).str.strip().replace("", "").ne("").any(), axis=0
    )
    df_clean = df_clean.loc[:, nonempty_col_mask].copy()

    # Drop Excel spillover columns like  / .1▍ tables_filtered, meta_df, all_sheets
